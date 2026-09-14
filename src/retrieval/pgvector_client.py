"""pgvector vector database client.

Handles vector storage and cosine similarity search using SQLAlchemy and pgvector extension.
"""

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import select

from src.database.models import KnowledgeChunk
from src.database.session import async_session_factory
from src.observability import get_logger

logger = get_logger(__name__)


class PgVectorManager:
    """Manages pgvector operations via SQLAlchemy."""

    def __init__(self) -> None:
        logger.info("pgvector_manager_initialized")

    async def ensure_collection(self) -> None:
        """Ensure vector extension and table exist.
        
        Handled during DB startup (init_db / migrations).
        """
        pass

    async def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        """Upsert document chunks with embeddings into PostgreSQL vector table."""
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have equal length"
            )

        async with async_session_factory() as session:
            for chunk, embedding in zip(chunks, embeddings):
                chunk_id = chunk.get("id")
                if isinstance(chunk_id, str):
                    chunk_id = uuid.UUID(chunk_id)
                elif chunk_id is None:
                    chunk_id = uuid.uuid4()

                kc = KnowledgeChunk(
                    id=chunk_id,
                    topic=chunk.get("topic", "rag"),
                    difficulty=chunk.get("difficulty", "beginner"),
                    source=chunk.get("source", ""),
                    chunk_text=chunk["text"],
                    embedding=embedding,
                )
                await session.merge(kc)
            await session.commit()

        logger.info("pgvector_upsert_completed", count=len(chunks))
        return len(chunks)

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        topic_filter: str | None = None,
        difficulty_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar document chunks using cosine distance.

        Args:
            query_vector: Query embedding vector.
            top_k: Number of results to return.
            topic_filter: Optional topic filter.
            difficulty_filter: Optional difficulty filter.

        Returns:
            List of search results with text, metadata, and similarity score.
        """
        distance_col = KnowledgeChunk.embedding.cosine_distance(query_vector).label("distance")
        stmt = select(KnowledgeChunk, distance_col)

        if topic_filter:
            stmt = stmt.where(KnowledgeChunk.topic == topic_filter)
        if difficulty_filter:
            stmt = stmt.where(KnowledgeChunk.difficulty == difficulty_filter)

        stmt = stmt.order_by(distance_col).limit(top_k)

        async with async_session_factory() as session:
            result = await session.execute(stmt)
            rows = result.all()

        search_results = []
        for chunk, dist in rows:
            score = 1.0 - float(dist) if dist is not None else 0.0
            search_results.append(
                {
                    "id": str(chunk.id),
                    "score": score,
                    "text": chunk.chunk_text,
                    "document_id": chunk.source,
                    "source": chunk.source,
                    "section": "",
                    "topic": chunk.topic,
                }
            )

        logger.info(
            "pgvector_search_completed",
            top_k=top_k,
            results_count=len(search_results),
            topic_filter=topic_filter,
        )
        return search_results

    async def close(self) -> None:
        """Close hook for client compatibility."""
        pass
