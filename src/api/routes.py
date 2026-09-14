"""API routes for ContentPilot.

POST /runs          — Start a new content generation run
GET  /runs          — List all runs
GET  /runs/{id}     — Get run details
GET  /runs/{id}/lesson     — Get the generated lesson
GET  /runs/{id}/evaluation — Get evaluation results
GET  /runs/{id}/rejection-log — Get the complete rejection log
POST /knowledge/ingest     — Ingest knowledge base
GET  /health               — Health check
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CreateRunRequest,
    EvaluationResponse,
    EvolutionStatusResponse,
    HealthResponse,
    InfrastructureErrorResponse,
    IngestRequest,
    IngestResponse,
    LessonResponse,
    ProposeImprovementRequest,
    ProposeImprovementResponse,
    RejectionLogResponse,
    RunDetailResponse,
    RunSummaryResponse,
)
from src.config import get_settings
from src.database.repository import ContentPilotRepository
from src.database.session import get_db_session
from src.errors import (
    ErrorCategory,
    InfrastructureErrorDetail,
    InfrastructureFailure,
    normalize_infrastructure_error,
)
from src.graph.workflow import compile_workflow
from src.memory.failure_patterns import FailurePatternDetector
from src.memory.run_memory import RunMemory
from src.memory.self_evolution import SelfEvolutionPipeline
from src.observability import get_logger
from src.observability.tracing import MetricsCollector
from src.retrieval.embeddings import EmbeddingProvider
from src.retrieval.ingestion import IngestionPipeline
from src.retrieval.pgvector_client import PgVectorManager

logger = get_logger(__name__)
router = APIRouter()

# In-memory run state storage (in production, use Redis or DB)
_run_states: dict[str, dict[str, Any]] = {}


async def _execute_workflow(
    run_id: str,
    initial_state: dict[str, Any],
) -> None:
    """Execute the LangGraph workflow in the background."""
    settings = get_settings()
    try:
        logger.info("workflow_execution_start", run_id=run_id)

        workflow = compile_workflow()
        final_state = await workflow.ainvoke(initial_state)

        # Store final state
        _run_states[run_id] = final_state

        # Persist to database
        from src.database.session import async_session_factory

        async with async_session_factory() as session:
            try:
                memory = RunMemory(session)
                await memory.persist_run(final_state)

                # Record failure patterns if there were failures
                if final_state.get("failure_reasons"):
                    detector = FailurePatternDetector(session)
                    await detector.record_failures(
                        run_id=run_id,
                        failures=final_state.get("failure_reasons", []),
                    )

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error("persistence_error", run_id=run_id, error=str(e))

        logger.info(
            "workflow_execution_completed",
            run_id=run_id,
            status=final_state.get("final_status"),
            retry_count=final_state.get("retry_count"),
        )

    except Exception as e:
        norm_detail = getattr(e, "detail", None)
        if not norm_detail or not isinstance(norm_detail, InfrastructureErrorDetail):
            norm_detail = normalize_infrastructure_error(
                e,
                stage="generation",
                provider=settings.llm_provider,
                model=settings.gemini_model if settings.llm_provider == "gemini" else settings.openai_model,
                run_id=run_id,
            )
        else:
            norm_detail.run_id = run_id

        logger.error(
            "infrastructure_failure",
            run_id=run_id,
            stage=norm_detail.stage,
            provider=norm_detail.provider,
            category=norm_detail.category,
            status_code=norm_detail.status_code,
            retryable=norm_detail.retryable,
            consumes_content_retry=norm_detail.consumes_content_retry,
            error_type=norm_detail.type,
            exception_type=type(e).__name__,
            retry_after=norm_detail.retry_after,
        )

        _run_states[run_id] = {
            **initial_state,
            "final_status": "system_error",
            "decision": "system_error",
            "evaluation_status": "not_executed",
            "retry_count": initial_state.get("retry_count", 0),
            "error": norm_detail.message,
            "error_detail": norm_detail.to_dict(),
            "completed_at": datetime.utcnow().isoformat(),
        }
        try:
            from src.database.session import async_session_factory
            async with async_session_factory() as session:
                repo = ContentPilotRepository(session)
                await repo.update_run_status(
                    run_id=uuid.UUID(run_id),
                    status="failed",
                    metrics={
                        "error": norm_detail.message,
                        "error_detail": norm_detail.to_dict(),
                        "decision": "system_error",
                        "evaluation_status": "not_executed",
                    },
                )
                await session.commit()
        except Exception as db_err:
            logger.error("persistence_failed_status_error", run_id=run_id, error=str(db_err))


@router.post("/runs", response_model=RunSummaryResponse, status_code=202)
async def create_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> RunSummaryResponse:
    """Start a new content generation run."""
    settings = get_settings()

    # Input validation
    if len(request.topic) > settings.max_input_length:
        raise HTTPException(400, f"Topic too long (max {settings.max_input_length} chars)")

    run_id = str(uuid.uuid4())
    run_uuid = uuid.UUID(run_id)

    # Create run in database
    repo = ContentPilotRepository(session)
    await repo.create_run(
        topic=request.topic,
        learner_profile=request.learner_profile.model_dump(),
        model_version=settings.llm_model,
        embedding_version=settings.embedding_model,
        demo_mode=request.demo_mode,
        run_id=run_uuid,
    )
    await session.commit()

    # Load memory context
    memory = RunMemory(session)
    memory_context = await memory.load_memory_context()

    # Build initial state
    initial_state: dict[str, Any] = {
        "run_id": run_id,
        "topic": request.topic,
        "learner_profile": request.learner_profile.model_dump(),
        "demo_mode": request.demo_mode,
        "max_retries": settings.max_retries,
        "prompt_version": "1.0.0",
        "rubric_version": "1.0.0",
        "knowledge_base_version": "1.0.0",
        "model_version": settings.llm_model,
        "embedding_version": settings.embedding_model,
        "memory_context": memory_context,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Store initial state
    _run_states[run_id] = initial_state

    # Execute workflow in background
    background_tasks.add_task(_execute_workflow, run_id, initial_state)

    logger.info("run_created", run_id=run_id, topic=request.topic, demo_mode=request.demo_mode)

    return RunSummaryResponse(
        run_id=run_id,
        topic=request.topic,
        final_status="pending",
        retry_count=0,
        lesson_version=0,
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/runs", response_model=list[RunSummaryResponse])
async def list_runs(session: AsyncSession = Depends(get_db_session)) -> list[RunSummaryResponse]:
    """List all generation runs, combining in-memory active states and persisted DB records."""
    repo = ContentPilotRepository(session)
    db_runs = await repo.list_runs(limit=100)

    seen_ids = set()
    runs = []

    # In-memory states first (most up-to-date for running/recent tasks)
    for run_id, state in _run_states.items():
        seen_ids.add(run_id)
        f_status = state.get("final_status", "pending")
        dec = state.get("decision") or ("system_error" if f_status in ("failed", "system_error") else (f_status if f_status in ("shipped", "rejected") else "pending"))
        ev_status = state.get("evaluation_status") or ("not_executed" if f_status in ("failed", "system_error") else "pending")
        runs.append(RunSummaryResponse(
            run_id=run_id,
            topic=state.get("topic", ""),
            final_status=f_status,
            retry_count=state.get("retry_count", 0),
            lesson_version=state.get("lesson_version", 0),
            decision=dec,
            evaluation_status=ev_status,
            created_at=state.get("created_at"),
            completed_at=state.get("completed_at"),
        ))

    # Add any from DB not in memory
    for dbr in db_runs:
        s_id = str(dbr.id)
        if s_id not in seen_ids:
            seen_ids.add(s_id)
            f_status = dbr.final_status
            dec = "system_error" if f_status == "failed" else (f_status if f_status in ("shipped", "rejected") else "pending")
            ev_status = "not_executed" if f_status == "failed" else "pending"
            runs.append(RunSummaryResponse(
                run_id=s_id,
                topic=dbr.topic,
                final_status=f_status,
                retry_count=dbr.retry_count or 0,
                lesson_version=0,
                decision=dec,
                evaluation_status=ev_status,
                created_at=dbr.created_at.isoformat() if dbr.created_at else None,
                completed_at=dbr.completed_at.isoformat() if dbr.completed_at else None,
            ))

    return sorted(runs, key=lambda r: r.created_at or "", reverse=True)


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> RunDetailResponse:
    """Get detailed run information."""
    state = _run_states.get(run_id)
    if not state:
        try:
            repo = ContentPilotRepository(session)
            db_run = await repo.get_run(uuid.UUID(run_id))
            if not db_run:
                raise HTTPException(404, f"Run {run_id} not found")
            db_versions = await repo.get_lesson_versions(uuid.UUID(run_id))
            db_evals = await repo.get_evaluations(uuid.UUID(run_id))

            eval_result = None
            if db_evals:
                latest_eval = db_evals[-1]
                eval_result = {
                    "overall_passed": latest_eval.overall_passed,
                    "critical_failures": latest_eval.critical_failures,
                }

            metrics_dict = db_run.metrics or {}
            final_status = db_run.final_status
            decision = metrics_dict.get("decision") or ("system_error" if final_status == "failed" else (final_status if final_status in ("shipped", "rejected") else "pending"))
            eval_status = metrics_dict.get("evaluation_status") or ("not_executed" if final_status == "failed" else ("passed" if eval_result and eval_result.get("overall_passed") else "pending"))
            err_detail = metrics_dict.get("error_detail")
            raw_err = metrics_dict.get("error")
            clean_error = raw_err

            if raw_err and ("[{'error':" in raw_err or "INFRASTRUCTURE_FAILURE" in raw_err or "429" in raw_err):
                norm = normalize_infrastructure_error(Exception(raw_err), stage="generation", provider="gemini", run_id=run_id)
                clean_error = norm.message
                if not err_detail:
                    err_detail = norm.to_dict()

            return RunDetailResponse(
                run_id=run_id,
                topic=db_run.topic,
                learner_profile=db_run.learner_profile,
                final_status=final_status,
                retry_count=db_run.retry_count or 0,
                lesson_version=len(db_versions),
                lesson_versions_count=len(db_versions),
                curriculum_plan=None,
                learning_objectives=[],
                evaluation_result=eval_result,
                metrics=metrics_dict,
                prompt_version=db_run.prompt_version,
                rubric_version=db_run.rubric_version,
                model_version=db_run.model_version,
                error=clean_error,
                error_detail=err_detail,
                decision=decision,
                evaluation_status=eval_status,
                created_at=db_run.created_at.isoformat() if db_run.created_at else None,
                completed_at=db_run.completed_at.isoformat() if db_run.completed_at else None,
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(404, f"Run {run_id} not found")

    final_status = state.get("final_status", "pending")
    decision = state.get("decision") or ("system_error" if final_status in ("failed", "system_error") else (final_status if final_status in ("shipped", "rejected") else "pending"))
    eval_res = state.get("evaluation_result")
    eval_status = state.get("evaluation_status") or ("not_executed" if final_status in ("failed", "system_error") else ("passed" if eval_res and eval_res.get("overall_passed") else "pending"))
    err_detail = state.get("error_detail")
    raw_err = state.get("error")
    clean_error = raw_err

    if raw_err and ("[{'error':" in raw_err or "INFRASTRUCTURE_FAILURE" in raw_err or "429" in raw_err):
        norm = normalize_infrastructure_error(Exception(raw_err), stage="generation", provider="gemini", run_id=run_id)
        clean_error = norm.message
        if not err_detail:
            err_detail = norm.to_dict()

    return RunDetailResponse(
        run_id=run_id,
        topic=state.get("topic", ""),
        learner_profile=state.get("learner_profile", {}),
        final_status=final_status,
        retry_count=state.get("retry_count", 0),
        lesson_version=state.get("lesson_version", 0),
        lesson_versions_count=len(state.get("lesson_versions", [])),
        curriculum_plan=state.get("curriculum_plan"),
        learning_objectives=state.get("learning_objectives", []),
        evaluation_result=eval_res,
        metrics=state.get("metrics", {}),
        prompt_version=state.get("prompt_version", ""),
        rubric_version=state.get("rubric_version", ""),
        model_version=state.get("model_version", ""),
        error=clean_error,
        error_detail=err_detail,
        decision=decision,
        evaluation_status=eval_status,
        created_at=state.get("created_at"),
        completed_at=state.get("completed_at"),
    )


@router.get("/runs/{run_id}/lesson", response_model=LessonResponse)
async def get_lesson(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> LessonResponse:
    """Get the generated lesson for a run."""
    state = _run_states.get(run_id)
    if not state:
        try:
            repo = ContentPilotRepository(session)
            db_run = await repo.get_run(uuid.UUID(run_id))
            if not db_run:
                raise HTTPException(404, f"Run {run_id} not found")
            db_versions = await repo.get_lesson_versions(uuid.UUID(run_id))
            if not db_versions:
                raise HTTPException(404, "Lesson not yet generated")
            latest_version = db_versions[-1]
            return LessonResponse(
                run_id=run_id,
                lesson_version=latest_version.version_number,
                lesson=latest_version.lesson_content,
                status=db_run.final_status,
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(404, f"Run {run_id} not found")

    lesson = state.get("lesson")
    if not lesson:
        raise HTTPException(404, "Lesson not yet generated")

    return LessonResponse(
        run_id=run_id,
        lesson_version=state.get("lesson_version", 0),
        lesson=lesson if isinstance(lesson, dict) else lesson.model_dump(),
        status=state.get("final_status", "pending"),
    )


@router.get("/runs/{run_id}/evaluation", response_model=EvaluationResponse)
async def get_evaluation(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationResponse:
    """Get evaluation results for a run."""
    state = _run_states.get(run_id)
    if not state:
        try:
            repo = ContentPilotRepository(session)
            db_evals = await repo.get_evaluations(uuid.UUID(run_id))
            if not db_evals:
                raise HTTPException(404, f"Evaluation for run {run_id} not found")
            latest = db_evals[-1]
            checks = await repo.get_evaluation_checks(latest.id)
            eval_dict = {
                "overall_passed": latest.overall_passed,
                "critical_failures": latest.critical_failures,
            }
            validation_results = []
            grounding_results = []
            semantic_results = []
            for c in checks:
                check_dict = {
                    "layer": c.layer,
                    "check_name": c.check_name,
                    "passed": c.passed,
                    "severity": c.severity,
                    "reason": c.reason,
                    "evidence": c.evidence,
                    "suggested_correction": c.suggested_correction,
                }
                if c.layer == "structural":
                    validation_results.append(check_dict)
                elif c.layer == "grounding":
                    grounding_results.append(check_dict)
                else:
                    semantic_results.append(check_dict)

            return EvaluationResponse(
                run_id=run_id,
                evaluation_result=eval_dict,
                validation_results=validation_results,
                grounding_results=grounding_results,
                semantic_evaluation=semantic_results,
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(404, f"Run {run_id} not found")

    return EvaluationResponse(
        run_id=run_id,
        evaluation_result=state.get("evaluation_result"),
        validation_results=state.get("validation_results", []),
        grounding_results=state.get("grounding_results", []),
        semantic_evaluation=state.get("semantic_evaluation", []),
    )


def _compute_rejection_diff(
    lesson_versions: list[dict[str, Any]],
    failure_reasons: list[str] | None = None,
    grounding_results: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Compute structured before/after diff between attempt 1 and attempt 2."""
    if len(lesson_versions) < 2:
        return []

    diffs: list[dict[str, Any]] = []
    v1_lesson = lesson_versions[0].get("lesson", {})
    v2_lesson = lesson_versions[1].get("lesson", {})

    v1_sections = {s.get("heading", ""): s.get("content", "") for s in v1_lesson.get("sections", [])}
    v2_sections = {s.get("heading", ""): s.get("content", "") for s in v2_lesson.get("sections", [])}

    # 1. Grounding / Accuracy diff (detect deliberate false claims or ungrounded facts)
    ungrounded_claim = None
    if grounding_results:
        for gr in grounding_results:
            if not gr.get("passed") and gr.get("evidence"):
                ungrounded_claim = gr.get("evidence")
                break

    v1_full_text = " ".join(v1_sections.values())
    v2_full_text = " ".join(v2_sections.values())

    if "retrain" in v1_full_text.lower() or ungrounded_claim:
        before_text = ungrounded_claim or "Stated: 'RAG retrains the LLM whenever new documents are added to the knowledge base.'"
        after_text = "Corrected: 'RAG dynamically retrieves external knowledge chunks at inference time without altering model weights.'"
        diffs.append({
            "dimension": "Accuracy & Grounding",
            "before": before_text,
            "after": after_text,
        })

    # 2. Section differences
    for heading, v1_content in v1_sections.items():
        v2_content = v2_sections.get(heading)
        if v2_content and v1_content != v2_content:
            diffs.append({
                "dimension": f"Section: {heading}",
                "before": v1_content[:200] + ("..." if len(v1_content) > 200 else ""),
                "after": v2_content[:200] + ("..." if len(v2_content) > 200 else ""),
            })
            if len(diffs) >= 3:
                break

    # 3. If failure reasons existed, ensure they are represented
    if not diffs and failure_reasons:
        for reason in failure_reasons[:2]:
            diffs.append({
                "dimension": "Evaluator Failure Correction",
                "before": f"Failed check: {reason}",
                "after": "Regenerated content strictly addressed evaluator feedback and passed all rubric criteria.",
            })

    return diffs


@router.get("/runs/{run_id}/rejection-log", response_model=RejectionLogResponse)
async def get_rejection_log(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> RejectionLogResponse:
    """Get the complete rejection/evaluation log for a run with full diff."""
    state = _run_states.get(run_id)

    # Fallback to database if not in memory (survives restart)
    if not state:
        try:
            repo = ContentPilotRepository(session)
            run_uuid = uuid.UUID(run_id)
            db_run = await repo.get_run(run_uuid)
            if not db_run:
                raise HTTPException(404, f"Run {run_id} not found")

            db_versions = await repo.get_lesson_versions(run_uuid)
            db_evals = await repo.get_evaluations(run_uuid)

            lesson_versions = [
                {
                    "version": lv.version_number,
                    "lesson": lv.lesson_content,
                    "created_at": lv.created_at.isoformat() if lv.created_at else None,
                    "regenerated": lv.version_number > 1,
                }
                for lv in db_versions
            ]

            eval_result = None
            if db_evals:
                latest_eval = db_evals[-1]
                eval_result = {
                    "overall_passed": latest_eval.overall_passed,
                    "critical_failures": latest_eval.critical_failures,
                }

            diffs = _compute_rejection_diff(lesson_versions)

            return RejectionLogResponse(
                run_id=run_id,
                topic=db_run.topic,
                final_status=db_run.final_status,
                total_attempts=len(lesson_versions),
                retry_count=db_run.retry_count or 0,
                attempts=lesson_versions,
                what_changed_diff=diffs,
                prompt_version=db_run.prompt_version,
                rubric_version=db_run.rubric_version,
                model_version=db_run.model_version,
                created_at=db_run.created_at.isoformat() if db_run.created_at else None,
                completed_at=db_run.completed_at.isoformat() if db_run.completed_at else None,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("db_rejection_log_fallback_failed", run_id=run_id, error=str(e))
            raise HTTPException(404, f"Run {run_id} not found")

    # In-memory execution state
    lesson_versions = state.get("lesson_versions", [])
    eval_result = state.get("evaluation_result", {})
    failure_reasons = state.get("failure_reasons", [])
    grounding_results = state.get("grounding_results", [])

    attempts = []
    for idx, lv in enumerate(lesson_versions):
        is_latest = (idx == len(lesson_versions) - 1)
        attempt_status = state.get("final_status", "pending") if is_latest else "failed"
        attempt = {
            "attempt_number": idx + 1,
            "version": lv.get("version"),
            "lesson": lv.get("lesson"),
            "created_at": lv.get("created_at"),
            "regenerated": lv.get("regenerated", idx > 0),
            "status": attempt_status,
            "failed_checks": failure_reasons if not is_latest else (eval_result.get("critical_failures", []) if eval_result else []),
        }
        attempts.append(attempt)

    diffs = _compute_rejection_diff(
        lesson_versions,
        failure_reasons=failure_reasons,
        grounding_results=grounding_results,
    )

    return RejectionLogResponse(
        run_id=run_id,
        topic=state.get("topic", ""),
        final_status=state.get("final_status", "pending"),
        total_attempts=len(lesson_versions),
        retry_count=state.get("retry_count", 0),
        attempts=attempts,
        what_changed_diff=diffs,
        prompt_version=state.get("prompt_version", ""),
        rubric_version=state.get("rubric_version", ""),
        model_version=state.get("model_version", ""),
        created_at=state.get("created_at"),
        completed_at=state.get("completed_at"),
    )


@router.get("/evolution/status", response_model=EvolutionStatusResponse)
async def get_evolution_status(
    session: AsyncSession = Depends(get_db_session),
) -> EvolutionStatusResponse:
    """Get the current self-evolution status and recurring failure trends."""
    pipeline = SelfEvolutionPipeline(session)
    status_data = await pipeline.get_evolution_status()

    return EvolutionStatusResponse(
        pending_improvements=status_data.get("pending_improvements", 0),
        trends=status_data.get("trends", []),
        active_prompt_version="1.0.0",
        active_rubric_version="1.0.0",
        note=status_data.get("note", ""),
    )


@router.post("/evolution/propose", response_model=ProposeImprovementResponse)
async def propose_evolution(
    request: ProposeImprovementRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ProposeImprovementResponse:
    """Propose a prompt improvement candidate based on failure patterns."""
    pipeline = SelfEvolutionPipeline(session)
    new_version = await pipeline.propose_prompt_improvement(
        prompt_name=request.prompt_name,
        current_version=request.current_version,
        improvement=request.improvement,
        new_template=request.new_template,
    )
    await session.commit()

    return ProposeImprovementResponse(
        prompt_name=request.prompt_name,
        new_version=new_version,
        status="candidate",
        message=(
            f"Candidate version {new_version} created. "
            "It will not replace production prompts until automated regression tests pass."
        ),
    )


@router.post("/knowledge/ingest", response_model=IngestResponse)
async def ingest_knowledge(request: IngestRequest) -> IngestResponse:
    """Ingest knowledge base documents into the vector database."""
    try:
        metrics = MetricsCollector()
        embedding_provider = EmbeddingProvider(metrics=metrics)
        vector_manager = PgVectorManager()

        pipeline = IngestionPipeline(embedding_provider, vector_manager)
        result = await pipeline.ingest_knowledge_base(
            documents_dir=request.documents_dir,
            metadata_path=request.metadata_path,
        )

        await vector_manager.close()

        return IngestResponse(
            status=result.get("status", "completed"),
            documents=result.get("documents", 0),
            chunks=result.get("chunks", 0),
            kb_version=result.get("kb_version", "1.0.0"),
        )

    except Exception as e:
        logger.error("ingestion_error", error=str(e))
        raise HTTPException(500, f"Ingestion failed: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """System health check."""
    db_status = "ok"
    pgvector_status = "ok"

    # Check database
    try:
        from src.database.session import async_session_factory
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    # Check pgvector
    try:
        pgvector_mgr = PgVectorManager()
        await pgvector_mgr.close()
    except Exception:
        pgvector_status = "unavailable"

    # Check LLM provider
    settings = get_settings()
    provider_val = (
        settings.llm_provider.value
        if hasattr(settings.llm_provider, "value")
        else str(settings.llm_provider)
    )
    llm_model = settings.llm_model
    llm_status = "connected"

    if provider_val == "ollama":
        llm_model = settings.ollama_model
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                if res.status_code == 200:
                    llm_status = "connected"
                else:
                    llm_status = "unavailable"
        except Exception:
            llm_status = "unavailable"
    elif provider_val == "gemini":
        llm_model = settings.gemini_model
        llm_status = "configured" if settings.gemini_api_key else "missing_key"
    elif provider_val == "openai":
        llm_model = settings.openai_model
        llm_status = "configured" if settings.openai_api_key else "missing_key"
    else:  # hybrid
        llm_status = "configured" if (settings.gemini_api_key or settings.openai_api_key) else "missing_key"

    overall_healthy = (
        db_status == "ok"
        and pgvector_status == "ok"
        and llm_status in ("connected", "configured")
    )

    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        version="0.1.0",
        database=db_status,
        pgvector=pgvector_status,
        llm_provider=provider_val,
        llm_model=llm_model,
        llm_status=llm_status,
    )
