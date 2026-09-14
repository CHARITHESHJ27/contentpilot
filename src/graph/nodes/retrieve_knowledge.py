"""Node 3: retrieve_knowledge — Search the knowledge base for relevant context."""

from datetime import datetime
from typing import Any

from src.observability import get_logger
from src.observability.tracing import MetricsCollector
from src.retrieval.embeddings import EmbeddingProvider
from src.retrieval.pgvector_client import PgVectorManager
from src.retrieval.pipeline import RetrievalPipeline

logger = get_logger(__name__)


async def retrieve_knowledge(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve relevant context from the knowledge base.

    Uses bounded retrieval (top-K) with metadata filtering.
    Does NOT send the entire knowledge base to the LLM.
    """
    logger.info("retrieve_knowledge_start", run_id=state.get("run_id"))

    topic = state.get("topic", "")
    metrics = MetricsCollector()

    embedding_provider = EmbeddingProvider(metrics=metrics)
    vector_manager = PgVectorManager()
    pipeline = RetrievalPipeline(
        embedding_provider=embedding_provider,
        vector_manager=vector_manager,
        metrics=metrics,
    )

    try:
        # Build a rich query from topic and learning objectives
        objectives = state.get("learning_objectives", [])
        query_parts = [f"Introduction to {topic}"]
        query_parts.extend(objectives[:3])  # Add top objectives for richer retrieval
        query = ". ".join(query_parts)

        # Execute retrieval pipeline
        results = await pipeline.retrieve(
            query=query,
            topic_filter="rag",
            difficulty_filter="beginner",
            rerank=True,
        )

        # Format context for the generator
        formatted_context = pipeline.format_context(results)
        sources = pipeline.extract_sources(results)

        logger.info(
            "retrieve_knowledge_completed",
            run_id=state.get("run_id"),
            results_count=len(results),
            sources=sources,
        )

        return {
            "retrieved_context": results,
            "retrieved_sources": sources,
            "formatted_context": formatted_context,
            "updated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("retrieve_knowledge_error", error=str(e), run_id=state.get("run_id"))
        # Graceful degradation — continue with empty context
        return {
            "retrieved_context": [],
            "retrieved_sources": [],
            "formatted_context": "No context available — knowledge base retrieval failed.",
            "error": f"Retrieval failed: {str(e)}",
            "updated_at": datetime.utcnow().isoformat(),
        }
    finally:
        await vector_manager.close()
