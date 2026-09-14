"""Hard pass/fail evaluation gate.

DETERMINISTIC application logic — NOT decided by the LLM.
A lesson ships ONLY when ALL hard requirements pass.
No averages, no partial credit.
"""

from src.graph.state import (
    EvaluationResult,
    GroundingResult,
    SemanticCheckResult,
    ValidationResult,
)
from src.observability import get_logger

logger = get_logger(__name__)

# Dimensions that MUST pass for shipping
REQUIRED_DIMENSIONS = {
    "accuracy",
    "grounding",
    "beginner_friendliness",
    "jargon_handling",
    "coverage",
    "teaching_by_example",
    "coherence",
    "clarity",
}


def evaluate_gate(
    validation_results: list[ValidationResult],
    grounding_results: list[GroundingResult],
    semantic_results: list[SemanticCheckResult],
) -> EvaluationResult:
    """Deterministic pass/fail gate for lesson shipping.

    Rules:
    1. Any critical structural validation failure → FAIL
    2. Any critical grounding failure → FAIL
    3. Any critical semantic dimension failure → FAIL
    4. All required dimensions must pass → otherwise FAIL
    """
    critical_failures: list[str] = []

    # Check structural validation
    for result in validation_results:
        if result.severity == "critical" and not result.passed:
            critical_failures.append(
                f"[structural] {result.check_name}: {result.message}"
            )

    # Check grounding
    for result in grounding_results:
        if not result.supported and result.severity == "critical":
            critical_failures.append(
                f"[grounding] Unsupported claim: {result.claim[:100]} — {result.reason}"
            )

    # Check semantic evaluation
    for result in semantic_results:
        if result.severity == "critical" and not result.passed:
            critical_failures.append(
                f"[semantic:{result.dimension}] {result.reason}"
            )

    # Check all required dimensions passed
    passed_dimensions = {r.dimension for r in semantic_results if r.passed}
    missing_dimensions = REQUIRED_DIMENSIONS - passed_dimensions
    for dim in missing_dimensions:
        critical_failures.append(
            f"[semantic:{dim}] Required dimension not passed"
        )

    overall_passed = len(critical_failures) == 0

    logger.info(
        "evaluation_gate_result",
        passed=overall_passed,
        critical_failures_count=len(critical_failures),
        passed_dimensions=sorted(passed_dimensions),
        missing_dimensions=sorted(missing_dimensions),
    )

    return EvaluationResult(
        overall_passed=overall_passed,
        critical_failures=critical_failures,
        validation_results=validation_results,
        grounding_results=grounding_results,
        semantic_results=semantic_results,
    )
