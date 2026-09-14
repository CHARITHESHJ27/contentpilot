"""Retrieval pipeline.

Query → Normalize → Embed → Metadata filter → Vector search → Top-K → Rerank → Context

Retrieval is independent from generation — clean separation of concerns.
"""

import time
from typing import Any

from src.config import get_settings
from src.observability import get_logger
from src.observability.tracing import MetricsCollector
from src.retrieval.embeddings import EmbeddingProvider
from src.retrieval.pgvector_client import PgVectorManager

logger = get_logger(__name__)


def _normalize_query(query: str) -> str:
    """Normalize a search query for better retrieval.

    Applies basic text normalization. In a production system,
    this could include query expansion, synonym injection, etc.
    """
    # Lowercase for consistency
    query = query.lower().strip()
    # Remove excessive punctuation
    query = query.replace("?", "").replace("!", "").replace(".", "")
    return query


def _simple_rerank(
    results: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    """Simple keyword-based reranking as a lightweight alternative to a cross-encoder.

    Boosts results that contain exact query terms.
    In production, use a cross-encoder model for better reranking.
    """
    query_terms = set(query.lower().split())

    for result in results:
        text = result.get("text", "").lower()
        # Count query term occurrences in the chunk
        term_hits = sum(1 for term in query_terms if term in text)
        # Boost the score by term relevance
        keyword_bonus = term_hits * 0.05
        result["reranked_score"] = result.get("score", 0.0) + keyword_bonus

    # Sort by reranked score
    results.sort(key=lambda r: r.get("reranked_score", 0.0), reverse=True)
    return results


class RetrievalPipeline:
    """Executes the full retrieval pipeline from query to ranked context.

    Keeps retrieval code independent from generation code.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_manager: PgVectorManager,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self.embeddings = embedding_provider
        self.vector_store = vector_manager
        self.metrics = metrics or MetricsCollector()
        settings = get_settings()
        self.default_top_k = settings.retrieval_top_k

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        topic_filter: str | None = None,
        difficulty_filter: str | None = None,
        rerank: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute the full retrieval pipeline.

        Args:
            query: The search query (e.g., a topic or question).
            top_k: Number of results to return (default from config).
            topic_filter: Optional topic metadata filter.
            difficulty_filter: Optional difficulty metadata filter.
            rerank: Whether to apply reranking.

        Returns:
            List of retrieved context chunks with metadata and scores.
        """
        start_time = time.time()
        k = top_k or self.default_top_k

        # Step 1: Normalize query
        normalized_query = _normalize_query(query)
        logger.info("retrieval_query_normalized", original=query, normalized=normalized_query)

        # Step 2: Embed query
        query_vector = await self.embeddings.embed_query(normalized_query)

        # Step 3: Vector search with metadata filtering
        # Retrieve more candidates than needed for reranking
        search_k = k * 2 if rerank else k

        results = await self.vector_store.search(
            query_vector=query_vector,
            top_k=search_k,
            topic_filter=topic_filter,
            difficulty_filter=difficulty_filter,
        )

        # Step 4: Rerank
        if rerank and len(results) > k:
            results = _simple_rerank(results, normalized_query)

        # Step 5: Take top-K
        final_results = results[:k]

        latency_ms = (time.time() - start_time) * 1000
        self.metrics.record_retrieval(latency_ms=latency_ms)

        logger.info(
            "retrieval_completed",
            query=query[:100],
            top_k=k,
            results_count=len(final_results),
            latency_ms=round(latency_ms, 2),
        )

        return final_results

    async def retrieve_for_grounding(
        self,
        claim: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Retrieve context specifically for grounding a claim.

        Uses a smaller top_k since we're checking a specific claim,
        not building general context.
        """
        return await self.retrieve(
            query=claim,
            top_k=top_k,
            rerank=True,
        )

    def format_context(self, results: list[dict[str, Any]]) -> str:
        """Format retrieved results into a context string for the LLM prompt.

        Args:
            results: Retrieved search results.

        Returns:
            Formatted context string with source references.
        """
        if not results:
            return "No relevant context found."

        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get("source", "unknown")
            section = result.get("section", "")
            text = result.get("text", "")
            score = result.get("score", 0.0)

            header = f"[Source {i}: {source}"
            if section:
                header += f" / {section}"
            header += f" (relevance: {score:.2f})]"

            context_parts.append(f"{header}\n{text}")

        return "\n\n---\n\n".join(context_parts)

    def extract_sources(self, results: list[dict[str, Any]]) -> list[str]:
        """Extract unique source document names from results."""
        sources = []
        seen = set()
        for result in results:
            source = result.get("source", "")
            if source and source not in seen:
                sources.append(source)
                seen.add(source)
        return sources
