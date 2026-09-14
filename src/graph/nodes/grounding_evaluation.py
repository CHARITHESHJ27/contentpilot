"""Node 7: grounding_evaluation — KB-grounded fact checking."""

from datetime import datetime
from typing import Any

from src.evaluation.grounding import run_grounding_evaluation
from src.observability import get_logger

logger = get_logger(__name__)


async def grounding_evaluation(state: dict[str, Any]) -> dict[str, Any]:
    """Run grounding evaluation against the knowledge base."""
    logger.info("grounding_evaluation_start", run_id=state.get("run_id"))

    lesson_data = state.get("lesson")
    if not lesson_data:
        return {"updated_at": datetime.utcnow().isoformat()}

    if not isinstance(lesson_data, dict):
        lesson_data = lesson_data.model_dump()

    try:
        results = await run_grounding_evaluation(lesson_data)
        return {
            "grounding_results": [r.model_dump() for r in results],
            "updated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("grounding_evaluation_error", error=str(e))
        return {
            "grounding_results": [{
                "claim": "grounding evaluation failed",
                "supported": False,
                "severity": "critical",
                "reason": f"Grounding evaluation error: {str(e)}",
            }],
            "updated_at": datetime.utcnow().isoformat(),
        }
