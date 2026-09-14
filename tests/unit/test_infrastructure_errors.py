"""Unit tests for clean infrastructure error handling vs content evaluation failures.

Verifies:
1. Provider 429 rate limit normalization (category, status code, no secret leakage).
2. Timeout normalization.
3. Authentication error normalization.
4. Database error normalization.
5. Background workflow execution halts on infrastructure failure without consuming content retries,
   setting decision="system_error", evaluation_status="not_executed", final_status="system_error".
6. Content quality failures continue to follow evaluation -> failure_analysis -> regenerate -> re-evaluate.
7. Max content retries exhaustion properly routes to reject with MAX_RETRIES_EXHAUSTED.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from openai import RateLimitError, APITimeoutError, AuthenticationError
from src.errors import (
    ErrorCategory,
    InfrastructureErrorDetail,
    InfrastructureFailure,
    normalize_infrastructure_error,
)
from src.graph.workflow import _route_after_evaluation


class TestInfrastructureErrorNormalization:
    """Test suite for centralized error normalization."""

    def test_rate_limit_429_normalized_cleanly(self):
        raw_error = Exception(
            "Error code: 429 - [{'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. https://ai.google.dev/gemini-api/docs/rate-limits limit: 5, model: gemini-3.5-flash Please retry in 267.59ms.', 'status': 'RESOURCE_EXHAUSTED'}}]"
        )
        detail = normalize_infrastructure_error(
            raw_error,
            stage="generation",
            provider="gemini",
            model="gemini-3.5-flash",
            run_id="test-run-123",
        )

        assert detail.type == "INFRASTRUCTURE_FAILURE"
        assert detail.category == ErrorCategory.RATE_LIMIT.value
        assert detail.status_code == 429
        assert detail.retryable is True
        assert detail.consumes_content_retry is False
        assert detail.provider == "gemini"
        assert detail.model == "gemini-3.5-flash"
        assert detail.run_id == "test-run-123"
        # Verify raw URL and raw JSON list/dict are stripped
        assert "https://" not in detail.message
        assert "[{'error':" not in detail.message
        assert "[{'error':" not in detail.detail
        assert "267.59ms" in detail.detail or "few moments" in detail.detail

    def test_timeout_error_normalized(self):
        timeout_err = APITimeoutError(request=MagicMock())
        detail = normalize_infrastructure_error(
            timeout_err,
            stage="generation",
            provider="openai",
            model="gpt-4o",
            run_id="timeout-run",
        )

        assert detail.type == "INFRASTRUCTURE_FAILURE"
        assert detail.category == ErrorCategory.TIMEOUT.value
        assert detail.status_code == 504
        assert detail.retryable is True
        assert detail.consumes_content_retry is False

    def test_authentication_error_normalized_non_retryable(self):
        auth_err = AuthenticationError(
            message="Invalid API key provided: sk-secret-12345",
            response=MagicMock(status_code=401),
            body=None,
        )
        detail = normalize_infrastructure_error(
            auth_err,
            stage="generation",
            provider="gemini",
            model="gemini-3.5-flash",
        )

        assert detail.category == ErrorCategory.AUTHENTICATION.value
        assert detail.status_code == 401
        assert detail.retryable is False
        assert detail.consumes_content_retry is False
        # Ensure secret API key is NOT in message or detail
        assert "sk-secret-12345" not in detail.message
        assert "sk-secret-12345" not in detail.detail

    def test_database_error_normalized(self):
        db_err = Exception("asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed")
        detail = normalize_infrastructure_error(
            db_err,
            stage="database",
            provider="postgres",
        )

        assert detail.category == ErrorCategory.DATABASE.value
        assert detail.status_code == 500
        assert detail.retryable is True
        assert detail.consumes_content_retry is False

    def test_to_dict_contract_stability(self):
        detail = InfrastructureErrorDetail(
            category=ErrorCategory.RATE_LIMIT.value,
            message="The AI provider is temporarily unavailable.",
            detail="Rate limit reached.",
            retryable=True,
            consumes_content_retry=False,
            provider="gemini",
            model="gemini-3.5-flash",
            stage="generation",
            status_code=429,
        )
        data = detail.to_dict()
        assert data["type"] == "INFRASTRUCTURE_FAILURE"
        assert data["category"] == "RATE_LIMIT"
        assert data["message"] == "The AI provider is temporarily unavailable."
        assert data["retryable"] is True
        assert data["consumes_content_retry"] is False


class TestWorkflowStateSeparation:
    """Verify infrastructure failure does NOT consume content retries or trigger rejection."""

    def test_evaluation_pass_routes_to_finalize(self):
        state = {
            "evaluation_result": {"overall_passed": True},
            "retry_count": 0,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "finalize"

    def test_content_failure_routes_to_analysis_and_retries(self):
        state = {
            "evaluation_result": {"overall_passed": False},
            "retry_count": 0,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "failure_analysis"

    def test_content_failure_routes_to_analysis_on_attempt_2(self):
        state = {
            "evaluation_result": {"overall_passed": False},
            "retry_count": 1,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "failure_analysis"

    def test_max_content_retries_exhausted_routes_to_reject(self):
        state = {
            "evaluation_result": {"overall_passed": False},
            "retry_count": 2,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "reject"

    @pytest.mark.asyncio
    async def test_infrastructure_failure_in_background_task_preserves_content_retry_budget(self):
        """Simulate an infrastructure failure during background workflow execution."""
        from src.api.routes import _execute_workflow, _run_states

        run_id = "test-infra-fail-run-uuid"
        initial_state = {
            "run_id": run_id,
            "topic": "Retrieval-Augmented Generation",
            "learner_profile": {},
            "retry_count": 0,
            "lesson_version": 0,
            "final_status": "pending",
        }
        _run_states[run_id] = initial_state

        # Mock compile_workflow to simulate rate limit 429
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(
            side_effect=RateLimitError(
                message="Resource has been exhausted (e.g. check quota)",
                response=MagicMock(status_code=429),
                body=None,
            )
        )

        with patch("src.api.routes.compile_workflow", return_value=mock_compiled):
            with patch("src.database.session.async_session_factory") as mock_session_factory:
                mock_session = AsyncMock()
                mock_session_factory.return_value.__aenter__.return_value = mock_session
                await _execute_workflow(run_id, initial_state)

        final_recorded_state = _run_states[run_id]

        # Assertions for infrastructure failure state
        assert final_recorded_state["final_status"] == "system_error"
        assert final_recorded_state["decision"] == "system_error"
        assert final_recorded_state["evaluation_status"] == "not_executed"
        # Content retry budget was NOT consumed
        assert final_recorded_state["retry_count"] == 0
        # Clean normalized error
        assert "rate limit" in final_recorded_state["error"].lower() or "unavailable" in final_recorded_state["error"].lower()
        assert final_recorded_state["error_detail"]["category"] == "RATE_LIMIT"
        assert final_recorded_state["error_detail"]["status_code"] == 429
        assert final_recorded_state["error_detail"]["consumes_content_retry"] is False
