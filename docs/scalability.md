# Scalability

This document details how the ContentPilot architecture is designed to scale from a local demo to a production-grade system.

## 1. Asynchronous I/O
The entire pipeline (FastAPI, pgvector client, PostgreSQL session, LLM provider calls) is fully asynchronous. This allows the system to handle many concurrent generation requests without blocking worker threads during long LLM inference times.

## 2. Stateless Processing
The LangGraph workflow operates on a discrete state object (`ContentPilotState`). The application server itself is stateless. This means multiple instances of the FastAPI server can run behind a load balancer, horizontally scaling to meet demand.

## 3. Batching & Deduplication
The ingestion pipeline processes documents in batches when calling the embedding API, preventing rate limits and improving throughput. It also computes cryptographic hashes of text chunks to ensure idempotency and prevent duplicate embeddings in pgvector.

## 4. Connection Pooling
PostgreSQL connections are managed via SQLAlchemy's async engine with connection pooling (`pool_size`, `max_overflow`), ensuring stable database performance under load.

## 5. Potential Bottlenecks & Future Optimizations
- **LLM Rate Limits & Redundancy**: The primary bottleneck in production is LLM provider rate limits (TPM/RPM). ContentPilot already implements active multi-provider fallback routing (Gemini ➔ OpenAI) in `LLMProvider`. Further production scaling can add provisioned throughput or distributed token buckets.
- **Worker Queues**: For very long generation tasks, HTTP connections might time out. The current system already offloads LangGraph execution to FastAPI background tasks, and future enterprise scale can transition to a distributed Celery or Temporal queue.
