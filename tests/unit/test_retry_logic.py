"""Unit tests for retry logic and workflow routing."""

import pytest

from src.graph.workflow import _route_after_evaluation


class TestRetryLogic:
    """Tests for the deterministic retry routing."""

    def test_pass_routes_to_finalize(self):
        state = {
            "evaluation_result": {"overall_passed": True},
            "retry_count": 0,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "finalize"

    def test_fail_within_retries_routes_to_analysis(self):
        state = {
            "evaluation_result": {"overall_passed": False},
            "retry_count": 0,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "failure_analysis"

    def test_fail_at_max_retries_routes_to_reject(self):
        state = {
            "evaluation_result": {"overall_passed": False},
            "retry_count": 2,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "reject"

    def test_fail_over_max_retries_routes_to_reject(self):
        state = {
            "evaluation_result": {"overall_passed": False},
            "retry_count": 5,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "reject"

    def test_retry_count_1_of_2_routes_to_analysis(self):
        state = {
            "evaluation_result": {"overall_passed": False},
            "retry_count": 1,
            "max_retries": 2,
        }
        assert _route_after_evaluation(state) == "failure_analysis"

    @pytest.mark.asyncio
    async def test_reject_node_sets_max_retries_exhausted(self):
        from src.graph.nodes.reject import reject
        state = {
            "run_id": "test-run",
            "retry_count": 2,
            "max_retries": 2,
            "lesson_version": 3,
            "failure_reasons": [{"issue": "Grounding failed"}],
        }
        result = await reject(state)
        assert result["final_status"] == "rejected"
        assert result["rejection_reason"] == "MAX_RETRIES_EXHAUSTED"
        assert result["metrics"]["rejection_reason"] == "MAX_RETRIES_EXHAUSTED"
