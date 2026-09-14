"""Layer 4 — Semantic evaluation using LLM judge.

Evaluates the lesson against 8 dimensions with strict PASS/FAIL criteria.
No partial credit. The evaluator does NOT blindly trust the generator.
"""

import json
from typing import Any

from src.graph.state import GeneratedLesson, LearnerProfile, SemanticCheckResult
from src.llm.prompts import SEMANTIC_EVALUATOR_PROMPT
from src.llm.provider import LLMProvider
from src.observability import get_logger

logger = get_logger(__name__)

REQUIRED_DIMENSIONS = [
    "accuracy",
    "grounding",
    "beginner_friendliness",
    "jargon_handling",
    "coverage",
    "teaching_by_example",
    "coherence",
    "clarity",
]


async def run_semantic_evaluation(
    lesson_data: dict[str, Any],
    learner_profile: dict[str, Any] | LearnerProfile,
    context: str,
) -> list[SemanticCheckResult]:
    """Run semantic evaluation against the 8-dimension rubric.

    Uses an LLM judge that is separate from the generator.
    Each dimension gets a strict PASS or FAIL verdict.
    """
    lesson = GeneratedLesson(**lesson_data)

    # Build full lesson text for evaluation
    parts = [f"# {lesson.title}"]
    parts.append("## What You Will Learn")
    for item in lesson.what_you_will_learn:
        parts.append(f"- {item}")
    for section in lesson.sections:
        parts.append(f"\n## {section.heading}\n{section.content}")
    if lesson.quiz:
        parts.append("\n## Mini Quiz")
        for i, q in enumerate(lesson.quiz, 1):
            parts.append(f"\nQ{i}: {q.question}")
            for j, opt in enumerate(q.options):
                parts.append(f"  {'ABCD'[j]}. {opt}")
    parts.append(f"\n## Summary\n{lesson.summary}")
    lesson_text = "\n".join(parts)

    # Handle learner profile
    if isinstance(learner_profile, dict):
        learner = LearnerProfile(**learner_profile)
    else:
        learner = learner_profile

    # Format evaluation prompt
    prompt = SEMANTIC_EVALUATOR_PROMPT.format(
        lesson_text=lesson_text,
        context=context,
        age_group=learner.age_group,
        country=learner.country,
        education_level=learner.education_level,
        language_background=learner.language_background,
        vocabulary_level=learner.vocabulary_level,
    )

    llm = LLMProvider()

    response = await llm.generate(
        system_prompt="You are a strict educational content evaluator. Return JSON only.",
        user_prompt=prompt,
        node_name="semantic_evaluation",
        temperature=0.0,
        max_tokens=4096,
    )

    # Parse evaluation results
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    results: list[SemanticCheckResult] = []

    try:
        parsed = json.loads(cleaned, strict=False)
        if isinstance(parsed, list):
            for item in parsed:
                dim = item.get("dimension", "").lower().replace(" ", "_")
                results.append(SemanticCheckResult(
                    dimension=dim,
                    passed=item.get("passed", False),
                    severity=item.get("severity", "critical"),
                    reason=item.get("reason", ""),
                    evidence=item.get("evidence"),
                    suggested_correction=item.get("suggested_correction"),
                ))
        elif isinstance(parsed, dict):
            # Handle dict format where keys are dimensions
            for dim, val in parsed.items():
                if isinstance(val, dict):
                    results.append(SemanticCheckResult(
                        dimension=dim.lower().replace(" ", "_"),
                        passed=val.get("passed", False),
                        severity=val.get("severity", "critical"),
                        reason=val.get("reason", ""),
                        evidence=val.get("evidence"),
                        suggested_correction=val.get("suggested_correction"),
                    ))
    except json.JSONDecodeError:
        logger.error("semantic_evaluation_parse_error", raw=response[:500])
        # Return all dimensions as failed if we can't parse
        for dim in REQUIRED_DIMENSIONS:
            results.append(SemanticCheckResult(
                dimension=dim,
                passed=False,
                severity="critical",
                reason="Failed to parse semantic evaluation response",
            ))

    # Ensure all required dimensions are covered
    covered = {r.dimension for r in results}
    for dim in REQUIRED_DIMENSIONS:
        if dim not in covered:
            results.append(SemanticCheckResult(
                dimension=dim,
                passed=False,
                severity="critical",
                reason=f"Dimension '{dim}' was not evaluated",
            ))

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    logger.info(
        "semantic_evaluation_completed",
        total_dimensions=len(results),
        passed=passed,
        failed=failed,
    )

    return results
