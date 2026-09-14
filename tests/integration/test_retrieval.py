"""Integration tests for the retrieval pipeline."""

import pytest
from src.retrieval.pipeline import _normalize_query, _simple_rerank

def test_query_normalization():
    """Test query normalization."""
    assert _normalize_query("What is RAG?") == "what is rag"
    assert _normalize_query("  Embedding! ") == "embedding"

def test_simple_rerank():
    """Test simple keyword-based reranking."""
    results = [
        {"text": "This is about retrieval.", "score": 0.5},
        {"text": "This is about generation.", "score": 0.6},
        {"text": "Retrieval augmented generation (RAG) is great.", "score": 0.4}
    ]
    query = "retrieval rag"
    
    reranked = _simple_rerank(results, query)
    
    # "retrieval augmented generation (RAG) is great." has both "retrieval" and "rag", so it should get a bonus.
    assert reranked[0]["text"] == "Retrieval augmented generation (RAG) is great."
