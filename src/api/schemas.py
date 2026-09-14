"""Pydantic request/response models for the API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Request Models ---

class LearnerProfileRequest(BaseModel):
    """Learner profile for content generation."""
    age_group: str = "17-18"
    education_level: str = "12th grade graduate"
    language_background: str = "non-English-medium"
    vocabulary_level: str = "limited English"
    career_goal: str = "start an AI career"
    country: str = "India"


class CreateRunRequest(BaseModel):
    """Request to create a new content generation run."""
    topic: str = Field(..., min_length=3, max_length=4000)
    learner_profile: LearnerProfileRequest = Field(default_factory=LearnerProfileRequest)
    demo_mode: Optional[str] = Field(
        None,
        description="Set to 'deliberate_failure' for demo mode",
    )


class IngestRequest(BaseModel):
    """Request to ingest knowledge base documents."""
    documents_dir: str = "knowledge/documents"
    metadata_path: str = "knowledge/metadata.json"


# --- Response Models ---

class InfrastructureErrorResponse(BaseModel):
    """Normalized infrastructure error representation."""
    type: str = "INFRASTRUCTURE_FAILURE"
    category: str
    message: str
    detail: str
    retryable: bool = True
    consumes_content_retry: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    stage: Optional[str] = None
    status_code: Optional[int] = None
    retry_after: Optional[str] = None
    run_id: Optional[str] = None


class RunSummaryResponse(BaseModel):
    """Summary of a generation run."""
    run_id: str
    topic: str
    final_status: str
    retry_count: int
    lesson_version: int
    decision: Optional[str] = None
    evaluation_status: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class RunDetailResponse(BaseModel):
    """Detailed view of a generation run."""
    run_id: str
    topic: str
    learner_profile: dict[str, Any]
    final_status: str
    retry_count: int
    lesson_version: int
    lesson_versions_count: int
    curriculum_plan: Optional[dict[str, Any]] = None
    learning_objectives: list[str] = Field(default_factory=list)
    evaluation_result: Optional[dict[str, Any]] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    prompt_version: str = ""
    rubric_version: str = ""
    model_version: str = ""
    error: Optional[str] = None
    error_detail: Optional[InfrastructureErrorResponse] = None
    decision: Optional[str] = None
    evaluation_status: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class LessonResponse(BaseModel):
    """The generated lesson content."""
    run_id: str
    lesson_version: int
    lesson: dict[str, Any]
    status: str


class EvaluationResponse(BaseModel):
    """Evaluation results for a run."""
    run_id: str
    evaluation_result: Optional[dict[str, Any]] = None
    validation_results: list[dict[str, Any]] = Field(default_factory=list)
    grounding_results: list[dict[str, Any]] = Field(default_factory=list)
    semantic_evaluation: list[dict[str, Any]] = Field(default_factory=list)


class RejectionLogResponse(BaseModel):
    """Complete rejection/evaluation log for a run."""
    run_id: str
    topic: str
    final_status: str
    total_attempts: int
    retry_count: int
    attempts: list[dict[str, Any]] = Field(default_factory=list)
    what_changed_diff: list[dict[str, Any]] = Field(default_factory=list)
    prompt_version: str = ""
    rubric_version: str = ""
    model_version: str = ""
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class EvolutionTrend(BaseModel):
    """Failure trend identified for self-evolution."""
    pattern_key: str
    description: str
    occurrences: int
    recommended_guardrail: str
    status: str = "proposed"


class EvolutionStatusResponse(BaseModel):
    """Current self-evolution and recurring failure pattern status."""
    pending_improvements: int
    trends: list[dict[str, Any]] = Field(default_factory=list)
    active_prompt_version: str = "1.0.0"
    active_rubric_version: str = "1.0.0"
    note: str


class ProposeImprovementRequest(BaseModel):
    """Request to propose an evolved prompt version."""
    prompt_name: str = "generator"
    current_version: str = "1.0.0"
    improvement: str
    new_template: str


class ProposeImprovementResponse(BaseModel):
    """Response after proposing an evolved prompt version."""
    prompt_name: str
    new_version: str
    status: str
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    pgvector: str


class IngestResponse(BaseModel):
    """Knowledge base ingestion response."""
    status: str
    documents: int
    chunks: int
    kb_version: str = ""
