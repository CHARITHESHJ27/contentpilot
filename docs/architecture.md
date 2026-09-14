# Architecture

This document describes the high-level architecture of the ContentPilot system.

## System-Level Flow

The system is designed as a monolithic FastAPI backend that acts as the controller for a LangGraph-powered agentic workflow.

1. **Client Interaction**: Clients (Web UI or API) submit a content generation request to the FastAPI server.
2. **LangGraph Workflow**: The FastAPI route invokes the LangGraph `StateGraph`, which controls the execution flow.
3. **Execution Steps**:
   - `load_memory`: Fetches past failure patterns to inject as guardrails.
   - `plan_curriculum`: Creates an outline for the content.
   - `retrieve_knowledge`: Searches PostgreSQL pgvector chunks for relevant canonical context.
   - `generate_lesson`: The LLM generates the lesson using structured output constraints.
   - `evaluate`: A multi-layer evaluation pipeline determines if the lesson is safe to ship.
   - `failure_analysis` & `regenerate`: If evaluation fails (and retry count < max), the system analyzes the failure and regenerates the content.
4. **Persistence**: The PostgreSQL database stores the generation run, all versioned lessons produced, and detailed evaluation checks.

## Key Technologies

- **FastAPI**: Backend web framework.
- **LangGraph**: State machine orchestrator for LLMs.
- **PostgreSQL + pgvector**: Unified database for relational metadata and vector embeddings.
- **Pydantic**: Data validation and type hinting.
- **structlog**: Structured JSON logging.
- **pytest**: Testing framework.
