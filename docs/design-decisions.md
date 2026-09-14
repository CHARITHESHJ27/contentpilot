# Design Decisions & Trade-offs

This document outlines key design decisions made during the architecture of ContentPilot.

## 1. LangGraph vs. Simple Chains
**Decision**: Use LangGraph.
**Rationale**: LangGraph provides an explicit state machine with typed state, conditional branching, and retry edges. Simple chains (like LCEL) cannot easily express cycles (e.g., regenerate upon failure) and make observability much harder.

## 2. Unified PostgreSQL with pgvector
**Decision**: Use PostgreSQL with `pgvector` for both relational metadata and vector embeddings.
**Rationale**: Unifying on PostgreSQL simplifies infrastructure, eliminates cross-database transactions, and allows atomic querying of runs, evaluations, and knowledge chunks. Native cosine distance (`<=>`) provides high-performance nearest-neighbor search directly in SQL without running a separate vector service.

## 3. Layered Evaluation vs. Single LLM Judge
**Decision**: Evaluate in 4 distinct layers (Structural → Deterministic → Grounding → Semantic).
**Rationale**: Failing fast on cheap deterministic checks (e.g., missing sections, prohibited claims) saves significant tokens and latency compared to running a slow, expensive LLM judge on structurally flawed content.

## 4. Hard Pass/Fail vs. Averaged Scoring
**Decision**: Any critical failure stops the lesson from shipping. No average scores are used to determine success.
**Rationale**: Averaged scores can hide critical safety or factual errors (e.g., a beautifully written lesson that hallucinated a core concept might score an 85% average). A hard gate ensures minimum quality bars are met.

## 5. Bounded Retries
**Decision**: Enforce a maximum of 2 retries (3 total attempts).
**Rationale**: Unbounded retries risk infinite loops and runaway API costs. If an LLM cannot fix an issue after 2 targeted feedback loops, it indicates a fundamental flaw in the prompt or rubric.
