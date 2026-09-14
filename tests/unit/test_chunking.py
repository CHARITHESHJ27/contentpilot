"""Unit tests for chunking and metadata in the ingestion pipeline."""

import pytest
from pathlib import Path

from src.retrieval.ingestion import (
    _chunk_text,
    _compute_chunk_hash,
    _normalize_text,
    parse_markdown_document,
)


class TestChunking:
    """Tests for text chunking."""

    def test_short_text_single_chunk(self):
        """Short text should produce a single chunk."""
        text = "This is a short piece of text."
        chunks = _chunk_text(text, chunk_size=512, chunk_overlap=64)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        """Long text should produce multiple overlapping chunks."""
        text = " ".join(["word"] * 1000)
        chunks = _chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        # Verify overlap exists
        for i in range(len(chunks) - 1):
            words_a = set(chunks[i].split()[-20:])
            words_b = set(chunks[i + 1].split()[:20:])
            assert len(words_a & words_b) > 0

    def test_empty_text(self):
        """Empty text should produce a single empty chunk."""
        chunks = _chunk_text("", chunk_size=512, chunk_overlap=64)
        assert len(chunks) == 1


class TestNormalization:
    """Tests for text normalization."""

    def test_whitespace_collapse(self):
        text = "Hello    world\n\n\nfoo"
        result = _normalize_text(text)
        assert "    " not in result

    def test_strip_lines(self):
        text = "  hello  \n  world  "
        result = _normalize_text(text)
        lines = result.split("\n")
        assert all(line == line.strip() for line in lines)


class TestChunkHash:
    """Tests for deduplication hashing."""

    def test_same_input_same_hash(self):
        h1 = _compute_chunk_hash("hello world", "doc-001")
        h2 = _compute_chunk_hash("hello world", "doc-001")
        assert h1 == h2

    def test_different_input_different_hash(self):
        h1 = _compute_chunk_hash("hello world", "doc-001")
        h2 = _compute_chunk_hash("goodbye world", "doc-001")
        assert h1 != h2

    def test_different_doc_different_hash(self):
        h1 = _compute_chunk_hash("hello world", "doc-001")
        h2 = _compute_chunk_hash("hello world", "doc-002")
        assert h1 != h2


class TestMarkdownParsing:
    """Tests for Markdown document parsing."""

    def test_parse_title_and_sections(self, tmp_path):
        doc = tmp_path / "test.md"
        doc.write_text("# My Title\n\n## Section 1\nContent 1\n\n## Section 2\nContent 2\n")
        result = parse_markdown_document(doc)
        assert result["title"] == "My Title"
        assert len(result["sections"]) == 2
        assert result["sections"][0]["heading"] == "Section 1"
