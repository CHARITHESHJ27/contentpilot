"""Layer 1 — Structural validation using Pydantic.

Validates that the lesson output has the correct structure,
all required fields, and passes basic schema checks.
"""

from typing import Any

from src.graph.state import GeneratedLesson, ValidationResult
from src.observability import get_logger

logger = get_logger(__name__)

REQUIRED_SECTION_HEADINGS = [
    "introduction",
    "problem before rag",
    "what rag means",
    "why rag is useful",
    "how rag works",
    "step-by-step",
    "real-world example",
    "rag architecture",
    "rag vs normal llm",
    "common misconceptions",
    "summary",
]


def validate_lesson_structure(lesson_data: dict[str, Any]) -> list[ValidationResult]:
    """Run all structural validation checks on a lesson.

    These are HARD FAILURES — the lesson cannot proceed
    to further evaluation if structural validation fails.
    """
    results: list[ValidationResult] = []

    # Check 1: Can it parse into GeneratedLesson?
    try:
        lesson = GeneratedLesson(**lesson_data)
    except Exception as e:
        results.append(ValidationResult(
            check_name="pydantic_parse",
            passed=False,
            severity="critical",
            message=f"Lesson does not match required schema: {str(e)[:200]}",
        ))
        return results  # Can't continue without valid structure

    results.append(ValidationResult(
        check_name="pydantic_parse",
        passed=True,
        severity="critical",
        message="Lesson structure is valid",
    ))

    # Check 2: Non-empty title
    if not lesson.title or len(lesson.title.strip()) < 5:
        results.append(ValidationResult(
            check_name="non_empty_title",
            passed=False,
            severity="critical",
            message="Lesson title is empty or too short",
        ))
    else:
        results.append(ValidationResult(
            check_name="non_empty_title",
            passed=True,
            severity="critical",
            message="Title is present and valid",
        ))

    # Check 3: Sections exist and are non-empty
    if not lesson.sections or len(lesson.sections) < 8:
        results.append(ValidationResult(
            check_name="minimum_sections",
            passed=False,
            severity="critical",
            message=f"Lesson has {len(lesson.sections)} sections, minimum 8 required",
        ))
    else:
        results.append(ValidationResult(
            check_name="minimum_sections",
            passed=True,
            severity="critical",
            message=f"Lesson has {len(lesson.sections)} sections",
        ))

    # Check 4: Non-empty section content
    empty_sections = [s.heading for s in lesson.sections if not s.content.strip()]
    if empty_sections:
        results.append(ValidationResult(
            check_name="non_empty_sections",
            passed=False,
            severity="critical",
            message=f"Empty sections found: {', '.join(empty_sections)}",
        ))
    else:
        results.append(ValidationResult(
            check_name="non_empty_sections",
            passed=True,
            severity="critical",
            message="All sections have content",
        ))

    # Check 5: Quiz validation
    if not lesson.quiz or len(lesson.quiz) < 3:
        results.append(ValidationResult(
            check_name="quiz_minimum_questions",
            passed=False,
            severity="major",
            message=f"Quiz has {len(lesson.quiz)} questions, minimum 3 required",
        ))
    else:
        results.append(ValidationResult(
            check_name="quiz_minimum_questions",
            passed=True,
            severity="major",
            message=f"Quiz has {len(lesson.quiz)} questions",
        ))

    # Check 6: Quiz option count
    for i, q in enumerate(lesson.quiz):
        if len(q.options) != 4:
            results.append(ValidationResult(
                check_name=f"quiz_options_count_q{i+1}",
                passed=False,
                severity="major",
                message=f"Quiz question {i+1} has {len(q.options)} options, expected 4",
            ))

    # Check 7: Valid correct_option_index
    for i, q in enumerate(lesson.quiz):
        if q.correct_option_index < 0 or q.correct_option_index >= len(q.options):
            results.append(ValidationResult(
                check_name=f"quiz_correct_index_q{i+1}",
                passed=False,
                severity="critical",
                message=f"Quiz question {i+1} has invalid correct_option_index: {q.correct_option_index}",
            ))

    # Check 8: What you will learn
    if not lesson.what_you_will_learn:
        results.append(ValidationResult(
            check_name="what_you_will_learn",
            passed=False,
            severity="major",
            message="'What you will learn' section is empty",
        ))
    else:
        results.append(ValidationResult(
            check_name="what_you_will_learn",
            passed=True,
            severity="major",
            message=f"'What you will learn' has {len(lesson.what_you_will_learn)} items",
        ))

    # Check 9: Summary
    if not lesson.summary or len(lesson.summary.strip()) < 50:
        results.append(ValidationResult(
            check_name="summary_present",
            passed=False,
            severity="major",
            message="Summary is missing or too short",
        ))
    else:
        results.append(ValidationResult(
            check_name="summary_present",
            passed=True,
            severity="major",
            message="Summary is present",
        ))

    logger.info(
        "structural_validation_completed",
        total_checks=len(results),
        passed=sum(1 for r in results if r.passed),
        failed=sum(1 for r in results if not r.passed),
    )

    return results
