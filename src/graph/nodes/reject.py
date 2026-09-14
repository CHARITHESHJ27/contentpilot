"""Node 13: reject — Reject a lesson that failed after max retries."""

from datetime import datetime
from typing import Any

from src.graph.state import FinalStatus
from src.observability import get_logger

logger = get_logger(__name__)


async def reject(state: dict[str, Any]) -> dict[str, Any]:
    """Reject a lesson that exhausted all retry attempts.

    Persists the complete rejection report for analysis.
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    failure_reasons = state.get("failure_reasons", [])

    if retry_count >= max_retries:
        reason = "MAX_RETRIES_EXHAUSTED"
    else:
        reason = "UNRECOVERABLE_EVALUATION_FAILURE"

    logger.warning(
        "lesson_rejected",
        run_id=state.get("run_id"),
        retry_count=retry_count,
        max_retries=max_retries,
        rejection_reason=reason,
        lesson_version=state.get("lesson_version"),
        failure_reasons=[
            f.get("issue", "") if isinstance(f, dict) else str(f) for f in failure_reasons
        ],
    )

    metrics = dict(state.get("metrics") or {})
    metrics["rejection_reason"] = reason

    return {
        "final_status": FinalStatus.REJECTED.value,
        "rejection_reason": reason,
        "metrics": metrics,
        "completed_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
