"""Document ingestion pipeline.

Documents → Parse → Normalize → Chunk → Add metadata → Embed → Store in pgvector

Designed for:
- Batching (process chunks in batches for efficient embedding API usage)
- Idempotency (chunk hashes prevent duplicate insertions)
- Incremental indexing (new documents can be added without reindexing)
- Document versioning (metadata tracks version)
"""

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.observability import get_logger
from src.retrieval.embeddings import EmbeddingProvider
from src.retrieval.pgvector_client import PgVectorManager

logger = get_logger(__name__)


def _normalize_text(text: str) -> str:
    """Normalize whitespace and clean up text."""
    # Collapse multiple whitespace characters
    text = re.sub(r"\s+", " ", text)
    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _compute_chunk_hash(text: str, document_id: str) -> str:
    """Compute a deterministic hash for deduplication."""
    content = f"{document_id}:{text}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[str]:
    """Split text into overlapping chunks by approximate token count.

    Uses a simple word-based approximation (1 token ≈ 0.75 words).
    For production, use a proper tokenizer like tiktoken.
    """
    words = text.split()
    # Approximate: 1 token ≈ 0.75 words, so chunk_size tokens ≈ chunk_size * 0.75 words
    words_per_chunk = int(chunk_size * 0.75)
    overlap_words = int(chunk_overlap * 0.75)

    if len(words) <= words_per_chunk:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + words_per_chunk
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap_words

    return chunks


def parse_markdown_document(file_path: Path) -> dict[str, Any]:
    """Parse a Markdown document and extract content and metadata.

    Returns:
        Dictionary with 'content', 'title', and 'sections'.
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    title = ""
    sections: list[dict[str, str]] = []
    current_section = ""
    current_content: list[str] = []

    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## "):
            if current_section:
                sections.append(
                    {"heading": current_section, "content": "\n".join(current_content).strip()}
                )
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)

    # Add the last section
    if current_section:
        sections.append(
            {"heading": current_section, "content": "\n".join(current_content).strip()}
        )

    return {
        "title": title,
        "content": text,
        "sections": sections,
    }


class IngestionPipeline:
    """Processes documents and stores them in the vector database.

    Pipeline: Parse → Normalize → Chunk → Metadata → Embed → Store
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_manager: PgVectorManager,
    ) -> None:
        self.embeddings = embedding_provider
        self.vector_store = vector_manager
        settings = get_settings()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    async def ingest_knowledge_base(
        self,
        documents_dir: str = "knowledge/documents",
        metadata_path: str = "knowledge/metadata.json",
    ) -> dict[str, Any]:
        """Ingest the entire knowledge base.

        Args:
            documents_dir: Path to the documents directory.
            metadata_path: Path to the metadata.json manifest.

        Returns:
            Ingestion summary with counts and status.
        """
        docs_path = Path(documents_dir)
        meta_path = Path(metadata_path)

        if not docs_path.exists():
            raise FileNotFoundError(f"Documents directory not found: {documents_dir}")

        # Load metadata manifest
        doc_metadata: dict[str, dict[str, str]] = {}
        kb_version = "1.0.0"
        if meta_path.exists():
            with open(meta_path) as f:
                manifest = json.load(f)
                kb_version = manifest.get("version", "1.0.0")
                for doc in manifest.get("documents", []):
                    doc_metadata[doc["filename"]] = doc

        # Ensure collection/table exists
        await self.vector_store.ensure_collection()

        # Process each document
        all_chunks: list[dict[str, Any]] = []
        total_documents = 0

        for md_file in sorted(docs_path.glob("*.md")):
            total_documents += 1
            doc_meta = doc_metadata.get(md_file.name, {})

            parsed = parse_markdown_document(md_file)
            normalized_content = _normalize_text(parsed["content"])

            # Chunk the document
            text_chunks = _chunk_text(
                normalized_content,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

            for idx, chunk_text in enumerate(text_chunks):
                chunk_hash = _compute_chunk_hash(chunk_text, doc_meta.get("id", md_file.stem))

                chunk = {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_hash)),
                    "text": chunk_text,
                    "document_id": doc_meta.get("id", md_file.stem),
                    "source": md_file.name,
                    "topic": doc_meta.get("topic", "rag"),
                    "section": doc_meta.get("section", ""),
                    "language": doc_meta.get("language", "en"),
                    "difficulty": doc_meta.get("difficulty", "beginner"),
                    "version": kb_version,
                    "chunk_index": idx,
                    "chunk_hash": chunk_hash,
                }
                all_chunks.append(chunk)

            logger.info(
                "document_parsed",
                file=md_file.name,
                chunks=len(text_chunks),
                doc_id=doc_meta.get("id", md_file.stem),
            )

        if not all_chunks:
            return {"status": "empty", "documents": 0, "chunks": 0}

        # Embed all chunks in batches
        batch_size = 50
        all_embeddings: list[list[float]] = []

        for i in range(0, len(all_chunks), batch_size):
            batch_texts = [c["text"] for c in all_chunks[i : i + batch_size]]
            batch_embeddings = await self.embeddings.embed_texts(batch_texts)
            all_embeddings.extend(batch_embeddings)

            logger.info(
                "embedding_batch_completed",
                batch=i // batch_size + 1,
                total_batches=(len(all_chunks) + batch_size - 1) // batch_size,
            )

        # Store in pgvector
        upserted = await self.vector_store.upsert_chunks(all_chunks, all_embeddings)

        summary = {
            "status": "completed",
            "documents": total_documents,
            "chunks": len(all_chunks),
            "upserted": upserted,
            "kb_version": kb_version,
        }

        logger.info("ingestion_completed", **summary)
        return summary

    async def ingest_single_document(
        self,
        file_path: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Ingest a single document (for incremental indexing).

        Args:
            file_path: Path to the document file.
            metadata: Optional metadata overrides.

        Returns:
            Ingestion result for this document.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        meta = metadata or {}
        parsed = parse_markdown_document(path)
        normalized = _normalize_text(parsed["content"])
        text_chunks = _chunk_text(normalized, self.chunk_size, self.chunk_overlap)

        chunks = []
        for idx, chunk_text in enumerate(text_chunks):
            chunk_hash = _compute_chunk_hash(chunk_text, meta.get("id", path.stem))
            chunks.append(
                {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_hash)),
                    "text": chunk_text,
                    "document_id": meta.get("id", path.stem),
                    "source": path.name,
                    "topic": meta.get("topic", "rag"),
                    "section": meta.get("section", ""),
                    "language": meta.get("language", "en"),
                    "difficulty": meta.get("difficulty", "beginner"),
                    "version": meta.get("version", "1.0.0"),
                    "chunk_index": idx,
                    "chunk_hash": chunk_hash,
                }
            )

        await self.vector_store.ensure_collection()
        embeddings = await self.embeddings.embed_texts([c["text"] for c in chunks])
        upserted = await self.vector_store.upsert_chunks(chunks, embeddings)

        return {
            "status": "completed",
            "file": path.name,
            "chunks": len(chunks),
            "upserted": upserted,
        }
