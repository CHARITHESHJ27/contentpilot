"""Node 6: deterministic_quality_check — Rule-based checks without LLM."""

from datetime import datetime
from typing import Any

from src.evaluation.deterministic import run_deterministic_checks
from src.observability import get_logger

logger = get_logger(__name__)


async def deterministic_quality_check(state: dict[str, Any]) -> dict[str, Any]:
    """Run deterministic quality checks on the lesson."""
    logger.info("deterministic_checks_start", run_id=state.get("run_id"))

    lesson_data = state.get("lesson")
    if not lesson_data:
        return {"updated_at": datetime.utcnow().isoformat()}

    if not isinstance(lesson_data, dict):
        lesson_data = lesson_data.model_dump()

    results = run_deterministic_checks(lesson_data)

    # Merge with existing validation results
    existing = state.get("validation_results", [])
    all_results = list(existing) + [r.model_dump() for r in results]

    return {
        "validation_results": all_results,
        "updated_at": datetime.utcnow().isoformat(),
    }
