"""Node 5: validate_structure — Pydantic structural validation."""

from datetime import datetime
from typing import Any

from src.evaluation.structural import validate_lesson_structure
from src.observability import get_logger

logger = get_logger(__name__)


async def validate_structure(state: dict[str, Any]) -> dict[str, Any]:
    """Run structural validation on the generated lesson."""
    logger.info("validate_structure_start", run_id=state.get("run_id"))

    lesson_data = state.get("lesson")
    if not lesson_data:
        return {
            "validation_results": [{
                "check_name": "lesson_exists",
                "passed": False,
                "severity": "critical",
                "message": "No lesson to validate",
            }],
            "updated_at": datetime.utcnow().isoformat(),
        }

    if isinstance(lesson_data, dict):
        results = validate_lesson_structure(lesson_data)
    else:
        results = validate_lesson_structure(lesson_data.model_dump())

    return {
        "validation_results": [r.model_dump() for r in results],
        "updated_at": datetime.utcnow().isoformat(),
    }
