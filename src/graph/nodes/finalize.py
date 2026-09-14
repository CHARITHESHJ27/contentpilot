"""Node 12: finalize — Ship a passing lesson."""

from datetime import datetime
from typing import Any

from src.graph.state import FinalStatus
from src.observability import get_logger

logger = get_logger(__name__)


async def finalize(state: dict[str, Any]) -> dict[str, Any]:
    """Finalize and ship a lesson that passed all evaluations."""
    logger.info(
        "finalize_start",
        run_id=state.get("run_id"),
        lesson_version=state.get("lesson_version"),
        retry_count=state.get("retry_count"),
    )

    return {
        "final_status": FinalStatus.SHIPPED.value,
        "completed_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
