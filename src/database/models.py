"""SQLAlchemy ORM models for ContentPilot persistence.

These models map directly to the database schema defined in the
implementation plan. All tables use UUID primary keys and UTC timestamps.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class GenerationRun(Base):
    """A single content generation run — one per topic submission."""

    __tablename__ = "generation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    learner_profile: Mapped[dict] = mapped_column(JSONB, nullable=False)
    final_status: Mapped[str] = mapped_column(
        Enum("pending", "shipped", "rejected", "failed", name="run_status"),
        default="pending",
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    prompt_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    rubric_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    kb_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    model_version: Mapped[str] = mapped_column(String(100), default="")
    embedding_version: Mapped[str] = mapped_column(String(100), default="")
    memory_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    demo_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    lesson_versions: Mapped[list["LessonVersion"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class LessonVersion(Base):
    """A versioned lesson produced during a generation run."""

    __tablename__ = "lesson_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generation_runs.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("generated", "passed", "failed", "rejected", name="lesson_status"),
        default="generated",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    run: Mapped["GenerationRun"] = relationship(back_populates="lesson_versions")
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="lesson_version"
    )


class Evaluation(Base):
    """An evaluation pass against a lesson version."""

    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generation_runs.id"), nullable=False
    )
    lesson_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lesson_versions.id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    critical_failures: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    run: Mapped["GenerationRun"] = relationship(back_populates="evaluations")
    lesson_version: Mapped["LessonVersion"] = relationship(
        back_populates="evaluations"
    )
    checks: Mapped[list["EvaluationCheck"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationCheck(Base):
    """Individual check result within an evaluation."""

    __tablename__ = "evaluation_checks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=False
    )
    layer: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # structural, deterministic, grounding, semantic
    check_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dimension: Mapped[str | None] = mapped_column(String(100), nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, major, minor
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_correction: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    evaluation: Mapped["Evaluation"] = relationship(back_populates="checks")


class FailurePattern(Base):
    """Aggregated recurring failure patterns across runs (long-term memory)."""

    __tablename__ = "failure_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pattern_key: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    recommended_guardrail: Mapped[str] = mapped_column(Text, nullable=False)
    sample_failures: Mapped[list] = mapped_column(JSONB, default=list)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class PromptVersion(Base):
    """Versioned prompts for controlled self-evolution."""

    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    prompt_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "candidate", "deprecated", name="prompt_status"),
        default="active",
    )
    regression_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class KnowledgeChunk(Base):
    """Vector embedding chunk for pgvector RAG store."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

