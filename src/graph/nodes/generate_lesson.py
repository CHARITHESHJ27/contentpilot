"""Node 4: generate_lesson — Generate a structured lesson using the LLM."""

import json
from datetime import datetime
from typing import Any

from src.graph.state import GeneratedLesson, LearnerProfile, LessonSection, QuizQuestion
from src.llm.prompts import (
    DELIBERATE_FAILURE_GENERATOR_PROMPT,
    GENERATOR_USER_PROMPT,
    format_generator_system_prompt,
)
from src.llm.provider import LLMProvider, StructuredOutputError
from src.observability import get_logger

logger = get_logger(__name__)


def _build_guardrails(memory_context: dict[str, Any] | None) -> str:
    """Build guardrail instructions from memory context."""
    if not memory_context:
        return ""

    guardrails = memory_context.get("guardrails", [])
    if not guardrails:
        return ""

    lines = ["GUARDRAILS FROM PAST FAILURES (follow these strictly):"]
    for i, g in enumerate(guardrails, 1):
        lines.append(f"{i}. {g}")
    return "\n".join(lines)


async def generate_lesson(state: dict[str, Any]) -> dict[str, Any]:
    """Generate a structured lesson using the LLM.

    Uses the curriculum plan, retrieved context, and learner profile
    to produce a lesson validated against the GeneratedLesson schema.
    """
    logger.info(
        "generate_lesson_start",
        run_id=state.get("run_id"),
        version=state.get("lesson_version", 0) + 1,
    )

    topic = state.get("topic", "")
    learner_data = state.get("learner_profile", {})
    learner = LearnerProfile(**learner_data) if isinstance(learner_data, dict) else learner_data

    context = state.get("formatted_context", "")
    curriculum_plan = json.dumps(state.get("curriculum_plan", {}), indent=2)
    objectives = "\n".join(f"- {obj}" for obj in state.get("learning_objectives", []))
    demo_mode = state.get("demo_mode")

    # Build guardrails from memory
    guardrails = _build_guardrails(state.get("memory_context"))

    # Format prompts
    system_prompt = format_generator_system_prompt(learner, guardrails=guardrails)

    # Use deliberate failure prompt for demo mode
    if demo_mode == "deliberate_failure":
        user_prompt = DELIBERATE_FAILURE_GENERATOR_PROMPT.format(
            topic=topic,
            context=context,
            curriculum_plan=curriculum_plan,
            objectives=objectives,
        )
        logger.warning("deliberate_failure_mode_active", run_id=state.get("run_id"))
    else:
        user_prompt = GENERATOR_USER_PROMPT.format(
            topic=topic,
            context=context,
            curriculum_plan=curriculum_plan,
            objectives=objectives,
        )

    llm = LLMProvider()

    try:
        lesson = await llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=GeneratedLesson,
            max_tokens=8192,
            node_name="generate_lesson",
        )
    except StructuredOutputError:
        # Retry once with a simpler prompt
        logger.warning("generate_lesson_structured_retry", run_id=state.get("run_id"))
        raw = await llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt + "\n\nIMPORTANT: Return ONLY valid JSON.",
            max_tokens=8192,
            node_name="generate_lesson_retry",
        )
        lesson = _parse_raw_lesson(raw)

    new_version = state.get("lesson_version", 0) + 1

    # Archive this version
    lesson_versions = list(state.get("lesson_versions", []))
    lesson_versions.append({
        "version": new_version,
        "lesson": lesson.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
    })

    logger.info(
        "generate_lesson_completed",
        run_id=state.get("run_id"),
        version=new_version,
        sections_count=len(lesson.sections),
        quiz_count=len(lesson.quiz),
    )

    return {
        "lesson": lesson.model_dump(),
        "lesson_version": new_version,
        "lesson_versions": lesson_versions,
        "updated_at": datetime.utcnow().isoformat(),
        # Clear previous evaluation state for the new version
        "validation_results": [],
        "grounding_results": [],
        "semantic_evaluation": [],
        "evaluation_result": None,
        "failure_reasons": [],
    }


def _parse_raw_lesson(raw: str) -> GeneratedLesson:
    """Best-effort parsing of raw LLM output into GeneratedLesson."""
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    data = json.loads(cleaned)

    # Normalize sections if they're in different formats
    sections = []
    for i, section in enumerate(data.get("sections", [])):
        if isinstance(section, dict):
            sections.append(LessonSection(
                heading=section.get("heading", f"Section {i+1}"),
                content=section.get("content", ""),
                order=section.get("order", i),
            ))

    quiz = []
    for q in data.get("quiz", []):
        if isinstance(q, dict):
            quiz.append(QuizQuestion(
                question=q.get("question", ""),
                options=q.get("options", []),
                correct_option_index=q.get("correct_option_index", 0),
                explanation=q.get("explanation", ""),
            ))

    return GeneratedLesson(
        title=data.get("title", "Untitled Lesson"),
        what_you_will_learn=data.get("what_you_will_learn", []),
        sections=sections,
        quiz=quiz,
        summary=data.get("summary", ""),
    )
