"""Node 11: regenerate_lesson — Regenerate lesson based on failure feedback."""

import json
from datetime import datetime
from typing import Any

from src.graph.nodes.generate_lesson import _parse_raw_lesson
from src.graph.state import GeneratedLesson, LearnerProfile
from src.llm.prompts import REGENERATOR_SYSTEM_PROMPT, REGENERATOR_USER_PROMPT, format_generator_system_prompt
from src.llm.provider import LLMProvider, StructuredOutputError
from src.observability import get_logger

logger = get_logger(__name__)


async def regenerate_lesson(state: dict[str, Any]) -> dict[str, Any]:
    """Regenerate the lesson incorporating evaluation feedback.

    Receives:
    - Current lesson (what's wrong)
    - Evaluation failures (what failed)
    - Retrieved context (authoritative information)
    - Curriculum plan (original structure)

    Produces a corrected lesson version.
    """
    logger.info(
        "regenerate_lesson_start",
        run_id=state.get("run_id"),
        retry_count=state.get("retry_count"),
    )

    topic = state.get("topic", "")
    learner_data = state.get("learner_profile", {})
    learner = LearnerProfile(**learner_data) if isinstance(learner_data, dict) else learner_data

    # Format failures for the regenerator
    failures = state.get("failure_reasons", [])
    failure_text = "\n".join(
        f"- [{f.get('severity', 'unknown').upper()}] {f.get('failed_dimension', '')}: "
        f"{f.get('issue', '')}"
        for f in failures
    )

    corrections_text = "\n".join(
        f"- {f.get('required_correction', '')}"
        for f in failures
    )

    # Get previous lesson as text
    lesson_data = state.get("lesson", {})
    if isinstance(lesson_data, dict):
        previous_lesson = json.dumps(lesson_data, indent=2)
    else:
        previous_lesson = json.dumps(lesson_data.model_dump(), indent=2)

    context = state.get("formatted_context", "")
    curriculum_plan = json.dumps(state.get("curriculum_plan", {}), indent=2)

    # Build guardrails
    memory_context = state.get("memory_context") or {}
    guardrails_list = memory_context.get("guardrails", [])
    guardrails = "\n".join(f"- {g}" for g in guardrails_list) if guardrails_list else ""

    system_prompt = REGENERATOR_SYSTEM_PROMPT.format(guardrails=guardrails)

    user_prompt = REGENERATOR_USER_PROMPT.format(
        topic=topic,
        failures=failure_text,
        corrections=corrections_text,
        context=context,
        curriculum_plan=curriculum_plan,
        previous_lesson=previous_lesson[:4000],  # Bounded context
    )

    llm = LLMProvider()

    try:
        lesson = await llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=GeneratedLesson,
            max_tokens=8192,
            node_name="regenerate_lesson",
        )
    except StructuredOutputError:
        # Fallback: try raw generation
        logger.warning("regenerate_structured_fallback", run_id=state.get("run_id"))
        raw = await llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt + "\n\nReturn ONLY valid JSON matching the schema.",
            max_tokens=8192,
            node_name="regenerate_lesson_fallback",
        )
        lesson = _parse_raw_lesson(raw)

    new_version = state.get("lesson_version", 0) + 1

    # Archive this version
    lesson_versions = list(state.get("lesson_versions", []))
    lesson_versions.append({
        "version": new_version,
        "lesson": lesson.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
        "regenerated": True,
        "retry_count": state.get("retry_count", 0),
    })

    logger.info(
        "regenerate_lesson_completed",
        run_id=state.get("run_id"),
        version=new_version,
        retry_count=state.get("retry_count"),
    )

    return {
        "lesson": lesson.model_dump(),
        "lesson_version": new_version,
        "lesson_versions": lesson_versions,
        "demo_mode": None,  # Clear demo mode after first generation
        "updated_at": datetime.utcnow().isoformat(),
        # Clear evaluation state for re-evaluation
        "validation_results": [],
        "grounding_results": [],
        "semantic_evaluation": [],
        "evaluation_result": None,
        "failure_reasons": [],
    }
