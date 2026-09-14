"""Failure pattern detection and aggregation.

Identifies recurring failure patterns across runs and stores them
for long-term memory and controlled self-evolution.
"""

import hashlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repository import ContentPilotRepository
from src.observability import get_logger

logger = get_logger(__name__)


def _generate_pattern_key(dimension: str, issue: str) -> str:
    """Generate a deterministic pattern key for deduplication."""
    # Normalize the issue to a canonical form
    normalized = issue.lower().strip()
    # Remove specific run details, keep the pattern
    for word in ["the", "a", "an", "is", "was", "were", "been"]:
        normalized = normalized.replace(f" {word} ", " ")
    content = f"{dimension}:{normalized}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


class FailurePatternDetector:
    """Detects and aggregates failure patterns across runs."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = ContentPilotRepository(session)

    async def record_failures(
        self,
        run_id: str,
        failures: list[dict[str, Any]],
    ) -> int:
        """Record failures from a run and update pattern counts.

        Returns the number of patterns updated/created.
        """
        patterns_updated = 0

        for failure in failures:
            dimension = failure.get("failed_dimension", "unknown")
            issue = failure.get("issue", "")
            severity = failure.get("severity", "major")
            correction = failure.get("required_correction", "")

            if not issue:
                continue

            pattern_key = _generate_pattern_key(dimension, issue)

            # Build recommended guardrail from the correction
            guardrail = correction or f"Avoid: {issue}"

            await self.repo.upsert_failure_pattern(
                pattern_key=pattern_key,
                description=f"[{dimension}] {issue}",
                recommended_guardrail=guardrail,
                sample_failure={
                    "run_id": run_id,
                    "dimension": dimension,
                    "issue": issue,
                    "severity": severity,
                },
            )
            patterns_updated += 1

        logger.info(
            "failure_patterns_recorded",
            run_id=run_id,
            patterns_updated=patterns_updated,
        )
        return patterns_updated

    async def get_active_guardrails(self, min_occurrences: int = 2) -> list[str]:
        """Get guardrails from recurring failure patterns.

        Only patterns that have occurred at least min_occurrences times
        are considered for guardrails. This prevents single-failure
        overreactions.
        """
        patterns = await self.repo.get_failure_patterns(min_occurrences)
        return [p.recommended_guardrail for p in patterns]
