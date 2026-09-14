"""Node 1: load_memory — Load failure patterns and guardrails from long-term memory.

Reads recurring failure patterns from PostgreSQL and injects
relevant guardrails into the workflow state for the generator.
"""

from datetime import datetime
from typing import Any

from src.graph.state import ContentPilotState
from src.observability import get_logger

logger = get_logger(__name__)


async def load_memory(state: dict[str, Any]) -> dict[str, Any]:
    """Load memory context from previous runs.

    Reads failure patterns from the database and constructs
    guardrails that influence (but don't override) generation.
    """
    logger.info("load_memory_start", run_id=state.get("run_id"))

    # Memory context will be populated by the workflow when DB is available
    # For now, initialize with empty context
    memory_context = state.get("memory_context") or {}

    # If failure patterns exist, format them as guardrails
    guardrails: list[str] = []
    failure_patterns = memory_context.get("failure_patterns", [])

    for pattern in failure_patterns:
        if pattern.get("occurrence_count", 0) >= 2:
            guardrails.append(pattern.get("recommended_guardrail", ""))

    memory_context["guardrails"] = guardrails
    memory_context["loaded_at"] = datetime.utcnow().isoformat()

    logger.info(
        "load_memory_completed",
        run_id=state.get("run_id"),
        guardrails_count=len(guardrails),
        patterns_count=len(failure_patterns),
    )

    return {
        "memory_context": memory_context,
        "updated_at": datetime.utcnow().isoformat(),
    }
