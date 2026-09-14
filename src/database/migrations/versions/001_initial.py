"""Initial schema — generation_runs, lesson_versions, evaluations, evaluation_checks,
failure_patterns, prompt_versions.

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    run_status = sa.Enum("pending", "shipped", "rejected", name="run_status")
    lesson_status = sa.Enum("generated", "passed", "failed", "rejected", name="lesson_status")
    prompt_status = sa.Enum("active", "candidate", "deprecated", name="prompt_status")

    run_status.create(op.get_bind(), checkfirst=True)
    lesson_status.create(op.get_bind(), checkfirst=True)
    prompt_status.create(op.get_bind(), checkfirst=True)

    # generation_runs
    op.create_table(
        "generation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("learner_profile", JSONB, nullable=False),
        sa.Column("final_status", run_status, server_default="pending"),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("prompt_version", sa.String(50), server_default="1.0.0"),
        sa.Column("rubric_version", sa.String(50), server_default="1.0.0"),
        sa.Column("kb_version", sa.String(50), server_default="1.0.0"),
        sa.Column("model_version", sa.String(100), server_default=""),
        sa.Column("embedding_version", sa.String(100), server_default=""),
        sa.Column("memory_context", JSONB, nullable=True),
        sa.Column("metrics", JSONB, nullable=True),
        sa.Column("demo_mode", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # lesson_versions
    op.create_table(
        "lesson_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id", UUID(as_uuid=True),
            sa.ForeignKey("generation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("lesson_content", JSONB, nullable=False),
        sa.Column("status", lesson_status, server_default="generated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # evaluations
    op.create_table(
        "evaluations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id", UUID(as_uuid=True),
            sa.ForeignKey("generation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_version_id", UUID(as_uuid=True),
            sa.ForeignKey("lesson_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer, nullable=False),
        sa.Column("overall_passed", sa.Boolean, nullable=False),
        sa.Column("critical_failures", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # evaluation_checks
    op.create_table(
        "evaluation_checks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evaluation_id", UUID(as_uuid=True),
            sa.ForeignKey("evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layer", sa.String(50), nullable=False),
        sa.Column("check_name", sa.String(200), nullable=False),
        sa.Column("dimension", sa.String(100), nullable=True),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("evidence", sa.Text, nullable=True),
        sa.Column("suggested_correction", sa.Text, nullable=True),
    )

    # failure_patterns
    op.create_table(
        "failure_patterns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pattern_key", sa.String(200), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("occurrence_count", sa.Integer, server_default="1"),
        sa.Column("recommended_guardrail", sa.Text, nullable=False),
        sa.Column("sample_failures", JSONB, server_default="[]"),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # prompt_versions
    op.create_table(
        "prompt_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("prompt_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("prompt_template", sa.Text, nullable=False),
        sa.Column("status", prompt_status, server_default="active"),
        sa.Column("regression_results", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes
    op.create_index("ix_generation_runs_topic", "generation_runs", ["topic"])
    op.create_index("ix_generation_runs_status", "generation_runs", ["final_status"])
    op.create_index("ix_lesson_versions_run_id", "lesson_versions", ["run_id"])
    op.create_index("ix_evaluations_run_id", "evaluations", ["run_id"])
    op.create_index("ix_evaluation_checks_eval_id", "evaluation_checks", ["evaluation_id"])
    op.create_index("ix_failure_patterns_key", "failure_patterns", ["pattern_key"])


def downgrade() -> None:
    op.drop_table("evaluation_checks")
    op.drop_table("evaluations")
    op.drop_table("lesson_versions")
    op.drop_table("generation_runs")
    op.drop_table("failure_patterns")
    op.drop_table("prompt_versions")

    op.execute("DROP TYPE IF EXISTS run_status")
    op.execute("DROP TYPE IF EXISTS lesson_status")
    op.execute("DROP TYPE IF EXISTS prompt_status")
