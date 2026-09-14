"""Node 8: semantic_evaluation — LLM judge evaluation."""

from datetime import datetime
from typing import Any

from src.evaluation.semantic import run_semantic_evaluation
from src.observability import get_logger

logger = get_logger(__name__)


async def semantic_evaluation(state: dict[str, Any]) -> dict[str, Any]:
    """Run semantic evaluation using LLM judge."""
    logger.info("semantic_evaluation_start", run_id=state.get("run_id"))

    lesson_data = state.get("lesson")
    if not lesson_data:
        return {"updated_at": datetime.utcnow().isoformat()}

    if not isinstance(lesson_data, dict):
        lesson_data = lesson_data.model_dump()

    learner_profile = state.get("learner_profile", {})
    context = state.get("formatted_context", "")

    try:
        results = await run_semantic_evaluation(lesson_data, learner_profile, context)
        return {
            "semantic_evaluation": [r.model_dump() for r in results],
            "updated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("semantic_evaluation_error", error=str(e))
        return {
            "semantic_evaluation": [],
            "error": f"Semantic evaluation error: {str(e)}",
            "updated_at": datetime.utcnow().isoformat(),
        }
