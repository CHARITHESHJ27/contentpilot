"""Node 2: plan_curriculum — Generate learning objectives and section sequence."""

import json
from datetime import datetime
from typing import Any

from src.graph.state import LearnerProfile
from src.llm.prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from src.llm.provider import LLMProvider
from src.observability import get_logger

logger = get_logger(__name__)


async def plan_curriculum(state: dict[str, Any]) -> dict[str, Any]:
    """Plan the curriculum for the lesson.

    Uses the LLM to create learning objectives and a logical
    section sequence based on the topic and learner profile.
    """
    logger.info("plan_curriculum_start", run_id=state.get("run_id"))

    topic = state.get("topic", "")
    learner = LearnerProfile(**state.get("learner_profile", {})) if isinstance(
        state.get("learner_profile"), dict
    ) else state.get("learner_profile", LearnerProfile())

    llm = LLMProvider()

    user_prompt = PLANNER_USER_PROMPT.format(
        topic=topic,
        age_group=learner.age_group,
        country=learner.country,
        education_level=learner.education_level,
        language_background=learner.language_background,
        vocabulary_level=learner.vocabulary_level,
        career_goal=learner.career_goal,
        kb_topics="RAG, retrieval, embeddings, vector databases, context, generation, architecture, comparisons, misconceptions",
    )

    response = await llm.generate(
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        node_name="plan_curriculum",
    )

    # Parse the curriculum plan
    try:
        # Strip markdown code fences
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        curriculum_plan = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("curriculum_plan_parse_fallback", raw_response=response[:300])
        curriculum_plan = {
            "learning_objectives": [
                "Understand what RAG is and why it exists",
                "Learn how retrieval works in RAG",
                "Understand embeddings and vector databases",
                "Learn how context is used in RAG",
                "Understand the complete RAG architecture",
                "Compare RAG with normal LLM usage",
                "Identify common misconceptions about RAG",
            ],
            "section_sequence": [
                "Introduction", "Problem Before RAG", "What RAG Means",
                "Why RAG is Useful", "How RAG Works", "Step-by-Step Explanation",
                "Real-World Example", "RAG Architecture",
                "RAG vs Normal LLM", "Common Misconceptions",
                "Mini Quiz", "Summary",
            ],
            "key_concepts": [
                "retrieval", "embeddings", "vector database",
                "context", "generation", "grounding",
            ],
        }

    learning_objectives = curriculum_plan.get("learning_objectives", [])

    logger.info(
        "plan_curriculum_completed",
        run_id=state.get("run_id"),
        objectives_count=len(learning_objectives),
    )

    return {
        "curriculum_plan": curriculum_plan,
        "learning_objectives": learning_objectives,
        "updated_at": datetime.utcnow().isoformat(),
    }
