"""Unit tests for PgVectorManager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from src.retrieval.pgvector_client import PgVectorManager


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pgvector_manager_init():
    manager = PgVectorManager()
    await manager.ensure_collection()
    await manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pgvector_upsert_length_mismatch():
    manager = PgVectorManager()
    chunks = [{"text": "hello"}]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    
    with pytest.raises(ValueError, match="must have equal length"):
        await manager.upsert_chunks(chunks, embeddings)


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.retrieval.pgvector_client.async_session_factory")
async def test_pgvector_upsert_success(mock_session_factory):
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    manager = PgVectorManager()
    chunks = [
        {
            "id": str(uuid.uuid4()),
            "text": "test chunk",
            "topic": "testing",
            "difficulty": "beginner",
            "source": "test.md",
        }
    ]
    embeddings = [[0.1] * 1536]

    count = await manager.upsert_chunks(chunks, embeddings)
    assert count == 1
    assert mock_session.merge.called
    assert mock_session.commit.called


@pytest.mark.unit
@pytest.mark.asyncio
@patch("src.retrieval.pgvector_client.async_session_factory")
async def test_pgvector_search_success(mock_session_factory):
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    mock_chunk = MagicMock()
    mock_chunk.id = uuid.uuid4()
    mock_chunk.chunk_text = "Retrieved text content"
    mock_chunk.source = "doc.md"
    mock_chunk.topic = "testing"

    mock_result = MagicMock()
    mock_result.all.return_value = [(mock_chunk, 0.1)]
    mock_session.execute.return_value = mock_result

    manager = PgVectorManager()
    results = await manager.search(
        query_vector=[0.1] * 1536,
        top_k=3,
        topic_filter="testing",
    )

    assert len(results) == 1
    assert results[0]["text"] == "Retrieved text content"
    assert pytest.approx(results[0]["score"], 0.01) == 0.90
