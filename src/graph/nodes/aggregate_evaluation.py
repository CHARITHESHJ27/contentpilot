"""Node 9: aggregate_evaluation — Combine all evaluation layers and apply gate."""

from datetime import datetime
from typing import Any

from src.evaluation.gate import evaluate_gate
from src.graph.state import GroundingResult, SemanticCheckResult, ValidationResult
from src.observability import get_logger

logger = get_logger(__name__)


async def aggregate_evaluation(state: dict[str, Any]) -> dict[str, Any]:
    """Aggregate all evaluation results and apply the hard pass/fail gate.

    The gate is DETERMINISTIC — not decided by the LLM.
    """
    logger.info("aggregate_evaluation_start", run_id=state.get("run_id"))

    # Parse results from state
    validation_results = [
        ValidationResult(**r) if isinstance(r, dict) else r
        for r in state.get("validation_results", [])
    ]
    grounding_results = [
        GroundingResult(**r) if isinstance(r, dict) else r
        for r in state.get("grounding_results", [])
    ]
    semantic_results = [
        SemanticCheckResult(**r) if isinstance(r, dict) else r
        for r in state.get("semantic_evaluation", [])
    ]

    # Apply deterministic gate
    evaluation_result = evaluate_gate(
        validation_results=validation_results,
        grounding_results=grounding_results,
        semantic_results=semantic_results,
    )

    logger.info(
        "aggregate_evaluation_completed",
        run_id=state.get("run_id"),
        overall_passed=evaluation_result.overall_passed,
        critical_failures=len(evaluation_result.critical_failures),
        retry_count=state.get("retry_count", 0),
    )

    return {
        "evaluation_result": evaluation_result.model_dump(),
        "updated_at": datetime.utcnow().isoformat(),
    }
