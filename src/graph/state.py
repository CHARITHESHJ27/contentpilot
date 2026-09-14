"""Typed LangGraph state for the ContentPilot workflow.

This is the single source of truth for all workflow state.
No important data is hidden in global variables.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional, TypedDict

from pydantic import BaseModel, Field


class FinalStatus(str, Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    REJECTED = "rejected"


class LearnerProfile(BaseModel):
    """Target learner characteristics that influence generation."""
    age_group: str = "17-18"
    education_level: str = "12th grade graduate"
    language_background: str = "non-English-medium"
    vocabulary_level: str = "limited English"
    career_goal: str = "start an AI career"
    country: str = "India"


class LessonSection(BaseModel):
    """A single section within the generated lesson."""
    heading: str
    content: str
    order: int


class QuizQuestion(BaseModel):
    """A quiz question with multiple-choice options."""
    question: str
    options: list[str]
    correct_option_index: int
    explanation: str


class GeneratedLesson(BaseModel):
    """Complete structured lesson output from the generator."""
    title: str
    what_you_will_learn: list[str]
    sections: list[LessonSection]
    quiz: list[QuizQuestion]
    summary: str


class ValidationResult(BaseModel):
    """Result of a structural or deterministic validation check."""
    check_name: str
    passed: bool
    severity: str  # "critical" | "major" | "minor"
    message: str


class GroundingResult(BaseModel):
    """Result of grounding a single claim against the knowledge base."""
    claim: str
    supported: bool
    evidence: Optional[str] = None
    source_document: Optional[str] = None
    severity: str = "critical"
    reason: str = ""


class SemanticCheckResult(BaseModel):
    """Result of a semantic evaluation dimension."""
    dimension: str
    passed: bool
    severity: str
    reason: str
    evidence: Optional[str] = None
    suggested_correction: Optional[str] = None


class EvaluationResult(BaseModel):
    """Aggregated evaluation result across all layers."""
    overall_passed: bool
    critical_failures: list[str] = Field(default_factory=list)
    validation_results: list[ValidationResult] = Field(default_factory=list)
    grounding_results: list[GroundingResult] = Field(default_factory=list)
    semantic_results: list[SemanticCheckResult] = Field(default_factory=list)


class FailureInstruction(BaseModel):
    """Structured regeneration instruction from failure analysis."""
    failed_dimension: str
    severity: str
    issue: str
    evidence: Optional[str] = None
    required_correction: str


class ContentPilotState(BaseModel):
    """Complete typed state for the LangGraph workflow.

    Every important piece of data flows through this state.
    No hidden globals, no side channels.
    """

    # --- Identity ---
    run_id: str = ""
    topic: str = ""
    learner_profile: LearnerProfile = Field(default_factory=LearnerProfile)
    demo_mode: Optional[str] = None  # "deliberate_failure" for demo

    # --- Planning ---
    learning_objectives: list[str] = Field(default_factory=list)
    curriculum_plan: Optional[dict[str, Any]] = None

    # --- Retrieval ---
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_sources: list[str] = Field(default_factory=list)
    formatted_context: str = ""

    # --- Generation ---
    lesson: Optional[GeneratedLesson] = None
    lesson_versions: list[dict[str, Any]] = Field(default_factory=list)
    lesson_version: int = 0

    # --- Evaluation ---
    validation_results: list[ValidationResult] = Field(default_factory=list)
    grounding_results: list[GroundingResult] = Field(default_factory=list)
    semantic_evaluation: list[SemanticCheckResult] = Field(default_factory=list)
    evaluation_result: Optional[EvaluationResult] = None

    # --- Failure & Regeneration ---
    failure_reasons: list[FailureInstruction] = Field(default_factory=list)
    regeneration_instructions: list[FailureInstruction] = Field(default_factory=list)

    # --- Retry Control (enforced by application code, NOT the LLM) ---
    retry_count: int = 0
    max_retries: int = 2

    # --- Memory ---
    memory_context: Optional[dict[str, Any]] = None

    # --- Versioning ---
    prompt_version: str = "1.0.0"
    rubric_version: str = "1.0.0"
    knowledge_base_version: str = "1.0.0"
    model_version: str = ""
    embedding_version: str = ""

    # --- Status ---
    final_status: FinalStatus = FinalStatus.PENDING

    # --- Timestamps ---
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    # --- Observability ---
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ContentPilotStateDict(TypedDict, total=False):
    """LangGraph workflow StateGraph schema.

    Allows LangGraph to preserve and merge all node dictionary updates
    without erasing state attributes between node executions.
    """
    run_id: str
    topic: str
    learner_profile: dict[str, Any]
    demo_mode: Optional[str]
    learning_objectives: list[str]
    curriculum_plan: Optional[dict[str, Any]]
    retrieved_context: list[dict[str, Any]]
    retrieved_sources: list[str]
    formatted_context: str
    lesson: Optional[dict[str, Any]]
    lesson_versions: list[dict[str, Any]]
    lesson_version: int
    validation_results: list[dict[str, Any]]
    grounding_results: list[dict[str, Any]]
    semantic_evaluation: list[dict[str, Any]]
    evaluation_result: Optional[dict[str, Any]]
    failure_reasons: list[dict[str, Any]]
    regeneration_instructions: list[dict[str, Any]]
    retry_count: int
    max_retries: int
    rejection_reason: Optional[str]
    memory_context: Optional[dict[str, Any]]
    prompt_version: str
    rubric_version: str
    knowledge_base_version: str
    model_version: str
    embedding_version: str
    final_status: str
    created_at: str
    updated_at: Optional[str]
    completed_at: Optional[str]
    metrics: dict[str, Any]
    error: Optional[str]
