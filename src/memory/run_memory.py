"""Run memory — persists complete run history to PostgreSQL."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repository import ContentPilotRepository
from src.observability import get_logger

logger = get_logger(__name__)


class RunMemory:
    """Persists and retrieves run history from the database."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = ContentPilotRepository(session)

    async def persist_run(self, state: dict[str, Any]) -> uuid.UUID:
        """Persist a completed run's state to the database."""
        run_id = uuid.UUID(state["run_id"])

        # Update run status
        await self.repo.update_run_status(
            run_id=run_id,
            status=state.get("final_status", "pending"),
            retry_count=state.get("retry_count", 0),
            metrics=state.get("metrics"),
            memory_context=state.get("memory_context"),
        )

        # Persist lesson versions
        for lv in state.get("lesson_versions", []):
            await self.repo.create_lesson_version(
                run_id=run_id,
                version_number=lv.get("version", 0),
                lesson_content=lv.get("lesson", {}),
            )

        # Persist evaluation result
        eval_result = state.get("evaluation_result", {})
        if eval_result:
            lesson_versions = await self.repo.get_lesson_versions(run_id)
            latest_lv = lesson_versions[-1] if lesson_versions else None

            if latest_lv:
                evaluation = await self.repo.create_evaluation(
                    run_id=run_id,
                    lesson_version_id=latest_lv.id,
                    attempt_number=state.get("retry_count", 0) + 1,
                    overall_passed=eval_result.get("overall_passed", False),
                    critical_failures=eval_result.get("critical_failures", []),
                )

                # Persist individual checks
                for layer, results_key in [
                    ("structural", "validation_results"),
                    ("grounding", "grounding_results"),
                    ("semantic", "semantic_results"),
                ]:
                    for check in eval_result.get(results_key, []):
                        await self.repo.create_evaluation_check(
                            evaluation_id=evaluation.id,
                            layer=layer,
                            check_name=check.get("check_name", check.get("dimension", check.get("claim", "unknown"))),
                            passed=check.get("passed", check.get("supported", False)),
                            severity=check.get("severity", "major"),
                            reason=check.get("message", check.get("reason", "")),
                            dimension=check.get("dimension"),
                            evidence=check.get("evidence"),
                            suggested_correction=check.get("suggested_correction"),
                        )

        logger.info("run_persisted", run_id=str(run_id), status=state.get("final_status"))
        return run_id

    async def load_memory_context(self) -> dict[str, Any]:
        """Load memory context for future runs.

        Reads failure patterns to inject guardrails into generation.
        """
        patterns = await self.repo.get_failure_patterns(min_occurrences=2)

        return {
            "failure_patterns": [
                {
                    "pattern_key": p.pattern_key,
                    "description": p.description,
                    "occurrence_count": p.occurrence_count,
                    "recommended_guardrail": p.recommended_guardrail,
                }
                for p in patterns
            ],
        }
