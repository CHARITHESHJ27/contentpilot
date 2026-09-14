"""Centralized error-normalization layer for ContentPilot.

Normalizes raw provider exceptions (Google Gemini, Groq, OpenAI, Postgres, etc.)
into clean, structured, and sanitized infrastructure failure objects.
Strictly prevents leaking API keys, Authorization headers, raw payloads,
internal URLs, or stack traces to callers and UI.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Any, Optional


class ErrorCategory(str, Enum):
    """Categorized infrastructure failure types."""
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    AUTHENTICATION = "AUTHENTICATION"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    DATABASE = "DATABASE"
    RETRIEVAL = "RETRIEVAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class InfrastructureErrorDetail:
    """Normalized infrastructure error representation.

    Conforms to the stable API error contract:
    {
      "type": "INFRASTRUCTURE_FAILURE",
      "category": "RATE_LIMIT",
      "message": "The content generation service is temporarily unavailable.",
      "detail": "AI provider rate limit reached. Please retry later.",
      "retryable": true,
      "consumes_content_retry": false
    }
    """
    type: str = "INFRASTRUCTURE_FAILURE"
    category: str = ErrorCategory.UNKNOWN.value
    message: str = "The content generation service encountered an unexpected error."
    detail: str = "An unexpected infrastructure error occurred. Please retry later."
    retryable: bool = True
    consumes_content_retry: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    stage: Optional[str] = None
    status_code: Optional[int] = None
    retry_after: Optional[str] = None
    run_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for JSON serialization and API responses."""
        return {
            "type": self.type,
            "category": self.category,
            "message": self.message,
            "detail": self.detail,
            "retryable": self.retryable,
            "consumes_content_retry": self.consumes_content_retry,
            "provider": self.provider,
            "model": self.model,
            "stage": self.stage,
            "status_code": self.status_code,
            "retry_after": self.retry_after,
            "run_id": self.run_id,
        }


class InfrastructureFailure(Exception):
    """Exception raised for normalized infrastructure failures."""

    def __init__(self, detail: InfrastructureErrorDetail, original_exc: Optional[Exception] = None) -> None:
        super().__init__(detail.message)
        self.detail = detail
        self.original_exc = original_exc


def _extract_retry_after(error_str: str) -> Optional[str]:
    """Attempt to extract human-readable retry delay from provider error text."""
    match = re.search(r"retry\s+in\s+([0-9\.]+(?:ms|s|m))", error_str, re.IGNORECASE)
    if match:
        return match.group(1)
    retry_delay_match = re.search(r"['\"]retryDelay['\"]\s*:\s*['\"]([^'\"]+)['\"]", error_str)
    if retry_delay_match:
        return retry_delay_match.group(1)
    return None


def normalize_infrastructure_error(
    exc: Exception,
    stage: str = "generation",
    provider: str = "unknown",
    model: str = "",
    run_id: str = "",
) -> InfrastructureErrorDetail:
    """Normalize any upstream exception into a sanitized, safe InfrastructureErrorDetail.

    Strips any raw JSON, auth tokens, Google RPC error dumps, or stack traces.
    """
    exc_type_name = type(exc).__name__
    raw_str = str(exc)

    # Check status code on exception if available (e.g. OpenAI/HTTP exceptions)
    status_code = getattr(exc, "status_code", None)
    if status_code is None and hasattr(exc, "response") and hasattr(exc.response, "status_code"):
        status_code = exc.response.status_code

    # Extract retry-after hint if present
    retry_after = _extract_retry_after(raw_str)

    # 1. Rate Limit / Quota Exceeded (429 / RESOURCE_EXHAUSTED)
    if (
        status_code == 429
        or "429" in raw_str
        or "RESOURCE_EXHAUSTED" in raw_str
        or "quota" in raw_str.lower()
        or "rate limit" in raw_str.lower()
        or exc_type_name in ("RateLimitError",)
    ):
        detail_msg = "AI provider rate limit or quota reached. Please retry in a few moments."
        if retry_after:
            detail_msg = f"AI provider rate limit reached. Please retry in {retry_after}."
        return InfrastructureErrorDetail(
            category=ErrorCategory.RATE_LIMIT.value,
            message="The AI provider is temporarily unavailable because a rate limit was reached.",
            detail=detail_msg,
            retryable=True,
            consumes_content_retry=False,
            provider=provider,
            model=model,
            stage=stage,
            status_code=429,
            retry_after=retry_after,
            run_id=run_id,
        )

    # 2. Timeout (504 / APITimeoutError)
    if (
        status_code in (408, 504)
        or "timeout" in raw_str.lower()
        or "timed out" in raw_str.lower()
        or exc_type_name in ("APITimeoutError", "TimeoutError", "ConnectTimeout", "ReadTimeout")
    ):
        return InfrastructureErrorDetail(
            category=ErrorCategory.TIMEOUT.value,
            message="The request to the AI provider timed out.",
            detail="The upstream model took too long to respond. Please retry the run.",
            retryable=True,
            consumes_content_retry=False,
            provider=provider,
            model=model,
            stage=stage,
            status_code=status_code or 504,
            run_id=run_id,
        )

    # 3. Authentication / Key Permission Errors (401 / 403)
    if (
        status_code in (401, 403)
        or "unauthorized" in raw_str.lower()
        or "api_key" in raw_str.lower()
        or "forbidden" in raw_str.lower()
        or exc_type_name in ("AuthenticationError", "PermissionDeniedError")
    ):
        return InfrastructureErrorDetail(
            category=ErrorCategory.AUTHENTICATION.value,
            message="AI provider authentication failed.",
            detail="The provider API credentials are invalid or lack required permissions.",
            retryable=False,
            consumes_content_retry=False,
            provider=provider,
            model=model,
            stage=stage,
            status_code=status_code or 401,
            run_id=run_id,
        )

    # 4. Provider Unavailable / Connection / Internal Server Error (500 / 502 / 503)
    if (
        status_code in (500, 502, 503)
        or "internal server error" in raw_str.lower()
        or "unavailable" in raw_str.lower()
        or "connection refused" in raw_str.lower()
        or "connecterror" in raw_str.lower()
        or "11434" in raw_str
        or "ollama" in raw_str.lower()
        or exc_type_name in ("InternalServerError", "ServiceUnavailableError", "APIConnectionError", "ConnectError", "ConnectionRefusedError")
    ):
        msg = "The AI provider service is temporarily unavailable."
        detail_msg = "Upstream model servers experienced an internal error. Please retry later."
        if provider == "ollama" or "11434" in raw_str or "ollama" in raw_str.lower():
            msg = "The Ollama local LLM service is temporarily unavailable."
            detail_msg = "Unable to connect to local Ollama service at http://localhost:11434. Please ensure Ollama is running ('ollama serve')."
        return InfrastructureErrorDetail(
            category=ErrorCategory.PROVIDER_UNAVAILABLE.value,
            message=msg,
            detail=detail_msg,
            retryable=True,
            consumes_content_retry=False,
            provider=provider,
            model=model,
            stage=stage,
            status_code=status_code or 503,
            run_id=run_id,
        )

    # 5. Invalid Response / Output Parsing Error
    if (
        exc_type_name in ("StructuredOutputError", "JSONDecodeError", "ValidationError")
        or "json" in raw_str.lower()
        or "parse" in raw_str.lower()
    ):
        return InfrastructureErrorDetail(
            category=ErrorCategory.INVALID_RESPONSE.value,
            message="The AI provider returned an invalid response structure.",
            detail="The model output could not be parsed into the required schema. Please retry.",
            retryable=True,
            consumes_content_retry=False,
            provider=provider,
            model=model,
            stage=stage,
            status_code=502,
            run_id=run_id,
        )

    # 6. Database / PostgreSQL / pgvector Failure
    if (
        "postgres" in raw_str.lower()
        or "asyncpg" in raw_str.lower()
        or "database" in raw_str.lower()
        or "sqlalchemy" in raw_str.lower()
        or exc_type_name in ("OperationalError", "DatabaseError", "PostgresError")
    ):
        return InfrastructureErrorDetail(
            category=ErrorCategory.DATABASE.value,
            message="The database service encountered a connection or storage error.",
            detail="Unable to read or persist state in PostgreSQL. Please check database health.",
            retryable=True,
            consumes_content_retry=False,
            provider="postgres",
            model="",
            stage="database",
            status_code=500,
            run_id=run_id,
        )

    # 7. Retrieval / Vector Search Failure
    if stage == "retrieval" or "retrieval" in raw_str.lower() or "embedding" in raw_str.lower():
        return InfrastructureErrorDetail(
            category=ErrorCategory.RETRIEVAL.value,
            message="Knowledge base retrieval failed.",
            detail="Unable to retrieve canonical vector embeddings from pgvector.",
            retryable=True,
            consumes_content_retry=False,
            provider=provider,
            model=model,
            stage="retrieval",
            status_code=500,
            run_id=run_id,
        )

    # 8. Default fallback: UNKNOWN Infrastructure Failure
    return InfrastructureErrorDetail(
        category=ErrorCategory.UNKNOWN.value,
        message="The content generation service encountered an unexpected infrastructure error.",
        detail="An internal server error interrupted processing. Please retry later.",
        retryable=True,
        consumes_content_retry=False,
        provider=provider,
        model=model,
        stage=stage,
        status_code=500,
        run_id=run_id,
    )
