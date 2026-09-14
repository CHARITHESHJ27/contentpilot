# ContentPilot — Self-Evaluating Agentic Content Generation System

**ContentPilot** is an enterprise-grade, self-evaluating agentic content generation system built to transform raw technical topics into high-quality, beginner-friendly educational lessons.

It accepts a target topic and learner profile, retrieves canonical knowledge from a **PostgreSQL `pgvector`** store, synthesizes structured lesson content via an agentic **LangGraph** workflow, evaluates output against a strict **4-Layer Evaluation Stack**, triggers self-correction loops upon failure, and visualizes execution metrics in a modern **Next.js App Router** frontend.

---

## 🌟 Key Features

- **Agentic LangGraph Workflow**: State machine orchestrating 6 execution steps (`load_memory` ➔ `plan_curriculum` ➔ `retrieve_knowledge` ➔ `generate_lesson` ➔ `evaluate` ➔ `failure_analysis`).
- **Unified `pgvector` RAG Engine**: Replaced external vector databases with PostgreSQL's native `pgvector` extension for seamless relational and vector query processing.
- **Strict 4-Layer Evaluation Stack**:
  - **Layer 1: Structural Validation** — Pydantic schema enforcing required JSON structures, quiz formatting, and option counts.
  - **Layer 2: Deterministic Quality Checks** — Word count boundaries (1500–8000), jargon density limit ($\le 15\%$), required concepts, and prohibited claim regex matching.
  - **Layer 3: Fact Grounding** — Claim extraction with automated evidence retrieval against `pgvector` to detect hallucinations.
  - **Layer 4: Semantic LLM Judge** — Pedagogical rubric evaluation assessing accuracy, clarity, coherence, and beginner friendliness.
- **Hard Pass/Fail Gate**: Any critical failure immediately blocks shipping and triggers self-correction retries.
- **Long-Term Memory & Failure Patterns**: Aggregates recurring failures across runs to inject dynamic guardrails into future prompts.
- **Next.js Standard Web Application**: Full-fledged Next.js 14+ App Router frontend featuring dark glassmorphic styling, live LangGraph step tracker, interactive assessment quiz renderer, 4-layer evaluation inspector, and `pgvector` knowledge base manager.

---

## 🏗 System Architecture

```
                       ┌────────────────────────────────────────┐
                       │   Next.js App Router Web UI (Port 3000)│
                       └───────────────────┬────────────────────┘
                                           │ API HTTP Requests
                                           ▼
                       ┌────────────────────────────────────────┐
                       │   FastAPI Backend Controller (Port 8000)│
                       └───────────────────┬────────────────────┘
                                           │ Workflow Orchestration
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 LangGraph StateGraph                                   │
│                                                                                        │
│  [1. Load Memory] ➔ [2. Plan Curriculum] ➔ [3. Retrieve Knowledge] ➔ [4. Generate]   │
│                                                                               │        │
│          [6. Failure Analysis & Retry] ◄────── [5. 4-Layer Evaluation] ◄──────┘        │
│                        │ (if passed)                                                   │
│                        ▼                                                               │
│                   [Ship Lesson]                                                        │
└────────────────────────┬───────────────────────────────────────────────────────────────┘
                         │
                         ▼
       ┌───────────────────────────────────┐
       │   PostgreSQL 16 + pgvector (5432)  │
       │  • Relational Tables & Versions   │
       │  • knowledge_chunks (Vector 1536) │
       └───────────────────────────────────┘
```

---

## 🚀 Quick Start (Docker Compose)

The easiest way to run the entire stack (PostgreSQL with `pgvector`, FastAPI backend, and Next.js Web UI) is using Docker Compose:

1. **Clone the repository and copy the environment template**:
   ```bash
   cp .env.example .env
   # Open .env and set your GEMINI_API_KEY (or OPENAI_API_KEY)
   ```

2. **Launch all services**:
   ```bash
   docker-compose up -d --build
   ```

3. **Ingest the Knowledge Base into `pgvector`**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/knowledge/ingest
   ```

4. **Access the Interfaces**:
   - **Next.js Web UI**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Backend Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 💻 Local Development Setup

### 1. Backend & Infrastructure Setup

Requires Python 3.11+ and PostgreSQL 16 with `pgvector`.

```bash
# Create and activate virtual environment using uv or venv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies in editable mode
uv pip install -e ".[dev]"

# Initialize database schema and pgvector extension
python -c "import asyncio; from src.database.session import init_db; asyncio.run(init_db())"

# Start the FastAPI backend server
uvicorn src.main:app --reload --port 8000
```

### 2. Next.js Frontend Setup

```bash
cd ui

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🦙 Local LLM with Ollama (`llama3.2`)

ContentPilot supports running **100% locally** with zero external cloud API dependencies using [Ollama](https://ollama.ai) and the lightweight, high-performance `llama3.2` model.

### 1. Install & Start Ollama
```bash
# Install Ollama (macOS / Linux / Windows)
brew install ollama  # macOS

# Pull the 3.2B parameters model (~2.0 GB)
ollama pull llama3.2

# Start the local daemon (runs on port 11434)
ollama serve
```

### 2. Configure ContentPilot for Ollama
In your `.env` file:
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

ContentPilot interfaces directly with Ollama's native OpenAI-compatible `/v1` endpoint. Structured schemas, JSON markdown fences, and conversational recovery are handled automatically. If the Ollama daemon is offline or interrupted, errors are normalized into clean `SYSTEM_ERROR` states without consuming pedagogical content retries.

---

## 🧪 Testing & Verification

Run unit tests and verification checks:

```bash
# Run unit test suite (57 tests covering chunking, checks, retry, fallback, evolution, infrastructure errors, pgvector, and Ollama)
.venv/bin/pytest tests/unit

# Verify Next.js production build
cd ui && npm run build
```

---

## 📂 Project Directory Structure

```
.
├── docker-compose.yml          # Postgres + pgvector, FastAPI App & Next.js Services
├── pyproject.toml              # Python dependencies & build config
├── src/
│   ├── api/                    # FastAPI routes & Pydantic schemas
│   ├── database/               # SQLAlchemy models (KnowledgeChunk with Vector) & sessions
│   ├── evaluation/             # 4-Layer evaluation stack (Structural, Deterministic, Grounding, Semantic)
│   ├── graph/                  # LangGraph state workflow nodes & orchestrator
│   ├── llm/                    # Hybrid Gemini & OpenAI provider client and prompt templates
│   ├── memory/                 # Failure pattern detection & long-term run memory
│   ├── observability/          # Structlog & OpenTelemetry tracing metrics
│   └── retrieval/              # pgvector client, embeddings & document ingestion pipeline
├── ui/                         # Next.js 14+ App Router Web Application
│   ├── app/                    # App Router pages (Dashboard, Layout, Styles)
│   ├── components/             # React UI components (Studio, Evaluation, Lesson, KB Manager)
│   ├── lib/                    # TypeScript API client
│   └── Dockerfile              # Container build for Next.js app
├── knowledge/                  # Canonical Markdown documents & metadata manifest
├── docs/                       # Architecture, evaluation strategy & design decisions
└── tests/                      # Pytest unit & integration test suites
```

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
