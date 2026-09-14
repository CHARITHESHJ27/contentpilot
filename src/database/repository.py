"""Data access layer for ContentPilot persistence.

All database interactions go through this repository.
Business logic should never directly execute SQL queries.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Evaluation,
    EvaluationCheck,
    FailurePattern,
    GenerationRun,
    LessonVersion,
    PromptVersion,
)
from src.observability import get_logger

logger = get_logger(__name__)


class ContentPilotRepository:
    """Data access layer for all ContentPilot entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Generation Runs ---

    async def create_run(
        self,
        topic: str,
        learner_profile: dict[str, Any],
        prompt_version: str = "1.0.0",
        rubric_version: str = "1.0.0",
        kb_version: str = "1.0.0",
        model_version: str = "",
        embedding_version: str = "",
        demo_mode: str | None = None,
        run_id: uuid.UUID | None = None,
    ) -> GenerationRun:
        """Create a new generation run."""
        run = GenerationRun(
            id=run_id or uuid.uuid4(),
            topic=topic,
            learner_profile=learner_profile,
            prompt_version=prompt_version,
            rubric_version=rubric_version,
            kb_version=kb_version,
            model_version=model_version,
            embedding_version=embedding_version,
            demo_mode=demo_mode,
        )
        self.session.add(run)
        await self.session.flush()
        logger.info("run_created", run_id=str(run.id), topic=topic)
        return run

    async def get_run(self, run_id: uuid.UUID) -> GenerationRun | None:
        """Get a generation run by ID."""
        result = await self.session.execute(
            select(GenerationRun).where(GenerationRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def update_run_status(
        self,
        run_id: uuid.UUID,
        status: str,
        retry_count: int | None = None,
        metrics: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
    ) -> None:
        """Update a run's status and optional fields."""
        values: dict[str, Any] = {
            "final_status": status,
            "completed_at": datetime.utcnow() if status in ("shipped", "rejected", "failed") else None,
        }
        if retry_count is not None:
            values["retry_count"] = retry_count
        if metrics is not None:
            values["metrics"] = metrics
        if memory_context is not None:
            values["memory_context"] = memory_context

        await self.session.execute(
            update(GenerationRun).where(GenerationRun.id == run_id).values(**values)
        )
        logger.info("run_status_updated", run_id=str(run_id), status=status)

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[GenerationRun]:
        """List generation runs ordered by creation time."""
        result = await self.session.execute(
            select(GenerationRun)
            .order_by(GenerationRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    # --- Lesson Versions ---

    async def create_lesson_version(
        self,
        run_id: uuid.UUID,
        version_number: int,
        lesson_content: dict[str, Any],
    ) -> LessonVersion:
        """Persist a new lesson version."""
        lesson = LessonVersion(
            run_id=run_id,
            version_number=version_number,
            lesson_content=lesson_content,
        )
        self.session.add(lesson)
        await self.session.flush()
        logger.info(
            "lesson_version_created",
            run_id=str(run_id),
            version=version_number,
        )
        return lesson

    async def update_lesson_status(
        self, lesson_id: uuid.UUID, status: str
    ) -> None:
        """Update a lesson version's status."""
        await self.session.execute(
            update(LessonVersion)
            .where(LessonVersion.id == lesson_id)
            .values(status=status)
        )

    async def get_lesson_versions(
        self, run_id: uuid.UUID
    ) -> list[LessonVersion]:
        """Get all lesson versions for a run."""
        result = await self.session.execute(
            select(LessonVersion)
            .where(LessonVersion.run_id == run_id)
            .order_by(LessonVersion.version_number)
        )
        return list(result.scalars().all())

    # --- Evaluations ---

    async def create_evaluation(
        self,
        run_id: uuid.UUID,
        lesson_version_id: uuid.UUID,
        attempt_number: int,
        overall_passed: bool,
        critical_failures: list[str],
    ) -> Evaluation:
        """Create an evaluation record."""
        evaluation = Evaluation(
            run_id=run_id,
            lesson_version_id=lesson_version_id,
            attempt_number=attempt_number,
            overall_passed=overall_passed,
            critical_failures=critical_failures,
        )
        self.session.add(evaluation)
        await self.session.flush()
        logger.info(
            "evaluation_created",
            run_id=str(run_id),
            attempt=attempt_number,
            passed=overall_passed,
        )
        return evaluation

    async def create_evaluation_check(
        self,
        evaluation_id: uuid.UUID,
        layer: str,
        check_name: str,
        passed: bool,
        severity: str,
        reason: str,
        dimension: str | None = None,
        evidence: str | None = None,
        suggested_correction: str | None = None,
    ) -> EvaluationCheck:
        """Create an individual evaluation check."""
        check = EvaluationCheck(
            evaluation_id=evaluation_id,
            layer=layer,
            check_name=check_name,
            dimension=dimension,
            passed=passed,
            severity=severity,
            reason=reason,
            evidence=evidence,
            suggested_correction=suggested_correction,
        )
        self.session.add(check)
        await self.session.flush()
        return check

    async def get_evaluations(self, run_id: uuid.UUID) -> list[Evaluation]:
        """Get all evaluations for a run."""
        result = await self.session.execute(
            select(Evaluation)
            .where(Evaluation.run_id == run_id)
            .order_by(Evaluation.attempt_number)
        )
        return list(result.scalars().all())

    async def get_evaluation_checks(
        self, evaluation_id: uuid.UUID
    ) -> list[EvaluationCheck]:
        """Get all checks for an evaluation."""
        result = await self.session.execute(
            select(EvaluationCheck)
            .where(EvaluationCheck.evaluation_id == evaluation_id)
            .order_by(EvaluationCheck.layer, EvaluationCheck.check_name)
        )
        return list(result.scalars().all())

    # --- Failure Patterns ---

    async def upsert_failure_pattern(
        self,
        pattern_key: str,
        description: str,
        recommended_guardrail: str,
        sample_failure: dict[str, Any] | None = None,
    ) -> FailurePattern:
        """Insert or update a failure pattern (increment count on duplicate)."""
        result = await self.session.execute(
            select(FailurePattern).where(FailurePattern.pattern_key == pattern_key)
        )
        pattern = result.scalar_one_or_none()

        if pattern:
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.utcnow()
            if sample_failure:
                samples = pattern.sample_failures or []
                samples.append(sample_failure)
                # Keep only last 10 samples
                pattern.sample_failures = samples[-10:]
            logger.info(
                "failure_pattern_updated",
                pattern_key=pattern_key,
                count=pattern.occurrence_count,
            )
        else:
            pattern = FailurePattern(
                pattern_key=pattern_key,
                description=description,
                recommended_guardrail=recommended_guardrail,
                sample_failures=[sample_failure] if sample_failure else [],
            )
            self.session.add(pattern)
            logger.info("failure_pattern_created", pattern_key=pattern_key)

        await self.session.flush()
        return pattern

    async def get_failure_patterns(
        self, min_occurrences: int = 1
    ) -> list[FailurePattern]:
        """Get failure patterns with at least min_occurrences."""
        result = await self.session.execute(
            select(FailurePattern)
            .where(FailurePattern.occurrence_count >= min_occurrences)
            .order_by(FailurePattern.occurrence_count.desc())
        )
        return list(result.scalars().all())

    # --- Prompt Versions ---

    async def get_active_prompt(self, prompt_name: str) -> PromptVersion | None:
        """Get the active version of a named prompt."""
        result = await self.session.execute(
            select(PromptVersion)
            .where(
                PromptVersion.prompt_name == prompt_name,
                PromptVersion.status == "active",
            )
            .order_by(PromptVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_prompt_version(
        self,
        prompt_name: str,
        version: str,
        prompt_template: str,
        status: str = "candidate",
    ) -> PromptVersion:
        """Create a new prompt version."""
        prompt = PromptVersion(
            prompt_name=prompt_name,
            version=version,
            prompt_template=prompt_template,
            status=status,
        )
        self.session.add(prompt)
        await self.session.flush()
        logger.info(
            "prompt_version_created",
            name=prompt_name,
            version=version,
            status=status,
        )
        return prompt

    # --- Rejection Log ---

    async def get_rejection_log(self, run_id: uuid.UUID) -> dict[str, Any]:
        """Build a complete rejection/evaluation log for a run."""
        run = await self.get_run(run_id)
        if not run:
            return {"error": "Run not found"}

        lesson_versions = await self.get_lesson_versions(run_id)
        evaluations = await self.get_evaluations(run_id)

        attempts = []
        for evaluation in evaluations:
            checks = await self.get_evaluation_checks(evaluation.id)
            attempt = {
                "attempt_number": evaluation.attempt_number,
                "overall_passed": evaluation.overall_passed,
                "critical_failures": evaluation.critical_failures,
                "checks": [
                    {
                        "layer": c.layer,
                        "check_name": c.check_name,
                        "dimension": c.dimension,
                        "passed": c.passed,
                        "severity": c.severity,
                        "reason": c.reason,
                        "evidence": c.evidence,
                        "suggested_correction": c.suggested_correction,
                    }
                    for c in checks
                ],
            }
            attempts.append(attempt)

        return {
            "run_id": str(run.id),
            "topic": run.topic,
            "final_status": run.final_status,
            "total_attempts": len(evaluations),
            "retry_count": run.retry_count,
            "prompt_version": run.prompt_version,
            "rubric_version": run.rubric_version,
            "model_version": run.model_version,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "attempts": attempts,
            "lesson_versions_count": len(lesson_versions),
        }
