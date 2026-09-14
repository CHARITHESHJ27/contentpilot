"""Controlled self-evolution pipeline.

Proposes prompt/rubric improvements based on failure history.
Improvements MUST be regression-tested before activation.
Never auto-modifies production prompts from a single failure.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repository import ContentPilotRepository
from src.observability import get_logger

logger = get_logger(__name__)


class SelfEvolutionPipeline:
    """Controlled improvement pipeline for prompts and rubrics.

    Pipeline:
    1. Aggregate failure patterns
    2. Identify recurring issues
    3. Propose improvement (candidate prompt)
    4. Run regression evaluation
    5. Approve/reject improvement
    6. Version the prompt/rubric
    """

    def __init__(self, session: AsyncSession) -> None:
        self.repo = ContentPilotRepository(session)

    async def analyze_failure_trends(
        self, min_occurrences: int = 3
    ) -> list[dict[str, Any]]:
        """Analyze failure patterns and identify improvement opportunities.

        Only considers patterns with min_occurrences to avoid
        reacting to one-off failures.
        """
        patterns = await self.repo.get_failure_patterns(min_occurrences)

        recommendations = []
        for pattern in patterns:
            recommendations.append({
                "pattern_key": pattern.pattern_key,
                "description": pattern.description,
                "occurrences": pattern.occurrence_count,
                "recommended_guardrail": pattern.recommended_guardrail,
                "status": "proposed",
            })

        logger.info(
            "failure_trends_analyzed",
            total_patterns=len(patterns),
            recommendations=len(recommendations),
        )

        return recommendations

    async def propose_prompt_improvement(
        self,
        prompt_name: str,
        current_version: str,
        improvement: str,
        new_template: str,
    ) -> str:
        """Propose a new prompt version as a candidate.

        The candidate is NOT activated until regression tests pass.
        """
        # Increment version
        parts = current_version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new_version = ".".join(parts)

        await self.repo.create_prompt_version(
            prompt_name=prompt_name,
            version=new_version,
            prompt_template=new_template,
            status="candidate",
        )

        logger.info(
            "prompt_improvement_proposed",
            prompt_name=prompt_name,
            current_version=current_version,
            new_version=new_version,
        )

        return new_version

    async def get_evolution_status(self) -> dict[str, Any]:
        """Get the current self-evolution status and pending improvements."""
        trends = await self.analyze_failure_trends(min_occurrences=2)

        return {
            "pending_improvements": len(trends),
            "trends": trends,
            "note": (
                "Improvements are proposed based on recurring patterns. "
                "They must be regression-tested before activation."
            ),
        }
