"""Node 10: failure_analysis — Produce structured regeneration instructions."""

from datetime import datetime
from typing import Any

from src.graph.state import EvaluationResult, FailureInstruction
from src.observability import get_logger

logger = get_logger(__name__)


async def failure_analysis(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze evaluation failures and produce actionable regeneration instructions.

    Does NOT simply say 'the lesson is bad'. Instead produces:
    - Failed dimension
    - Severity
    - Exact issue
    - Evidence
    - Required correction
    """
    logger.info(
        "failure_analysis_start",
        run_id=state.get("run_id"),
        retry_count=state.get("retry_count", 0),
    )

    eval_data = state.get("evaluation_result", {})
    if isinstance(eval_data, dict):
        evaluation = EvaluationResult(**eval_data)
    else:
        evaluation = eval_data

    instructions: list[FailureInstruction] = []

    # Analyze structural/deterministic failures
    for result in evaluation.validation_results:
        if not result.passed and result.severity in ("critical", "major"):
            instructions.append(FailureInstruction(
                failed_dimension=f"structural:{result.check_name}",
                severity=result.severity,
                issue=result.message,
                required_correction=f"Fix the structural issue: {result.message}",
            ))

    # Analyze grounding failures
    for result in evaluation.grounding_results:
        if not result.supported and result.severity in ("critical", "major"):
            instructions.append(FailureInstruction(
                failed_dimension="grounding",
                severity=result.severity,
                issue=f"Unsupported claim: {result.claim}",
                evidence=result.reason,
                required_correction=(
                    f"Remove or correct the unsupported claim. "
                    f"Ground the explanation in factual information. "
                    f"Reason: {result.reason}"
                ),
            ))

    # Analyze semantic failures
    for result in evaluation.semantic_results:
        if not result.passed and result.severity in ("critical", "major"):
            instructions.append(FailureInstruction(
                failed_dimension=f"semantic:{result.dimension}",
                severity=result.severity,
                issue=result.reason,
                evidence=result.evidence,
                required_correction=result.suggested_correction or f"Fix the {result.dimension} issue",
            ))

    # Increment retry count (application-level control, NOT LLM)
    new_retry_count = state.get("retry_count", 0) + 1

    logger.info(
        "failure_analysis_completed",
        run_id=state.get("run_id"),
        instructions_count=len(instructions),
        new_retry_count=new_retry_count,
    )

    return {
        "failure_reasons": [i.model_dump() for i in instructions],
        "regeneration_instructions": [i.model_dump() for i in instructions],
        "retry_count": new_retry_count,
        "updated_at": datetime.utcnow().isoformat(),
    }
