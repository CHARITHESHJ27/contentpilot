# RAG Architecture

## End-to-End RAG Pipeline

The complete RAG architecture consists of two main phases: **Indexing** (offline) and **Querying** (online).

## Phase 1: Indexing (Offline / Preparation)

This phase prepares the knowledge base for fast retrieval. It happens before any user query.

### Steps:

1. **Document Collection**: Gather source documents (PDFs, web pages, text files, databases).
2. **Parsing**: Extract text content from various document formats.
3. **Chunking**: Split documents into smaller, manageable pieces (chunks). Typical chunk sizes are 256-1024 tokens.
4. **Embedding**: Convert each chunk into a numerical vector using an embedding model.
5. **Storing**: Store the vectors in a vector database along with the original text and metadata.

### Diagram:

```
Documents → Parse → Chunk → Embed → Store in Vector DB
```

## Phase 2: Querying (Online / Runtime)

This phase handles actual user queries in real-time.

### Steps:

1. **User Query**: The user asks a question.
2. **Query Embedding**: The question is converted into a vector using the same embedding model.
3. **Retrieval**: The vector database is searched for the most similar document chunks.
4. **Context Assembly**: The top-K retrieved chunks are assembled as context.
5. **Prompt Construction**: The context + question are formatted into a prompt.
6. **Generation**: The LLM generates a response based on the prompt.
7. **Response**: The generated response is returned to the user.

### Diagram:

```
User Question → Embed Query → Search Vector DB → Get Top-K Chunks
→ Assemble Context → Build Prompt → LLM Generates Response → Return Answer
```

## Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    INDEXING PHASE                     │
│                                                      │
│  Documents → Parser → Chunker → Embedder → Vector DB │
│                                                      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                    QUERY PHASE                       │
│                                                      │
│  User Query → Embedder → Vector DB Search            │
│                              ↓                       │
│                    Retrieved Chunks                   │
│                              ↓                       │
│              Prompt = Context + Question             │
│                              ↓                       │
│                      LLM Generation                  │
│                              ↓                       │
│                    Grounded Response                  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Key Architectural Principles

1. **Separation of concerns**: Retrieval and generation are independent components.
2. **Modularity**: Each component (embedder, retriever, generator) can be swapped independently.
3. **Scalability**: The vector database can scale to millions of documents.
4. **Bounded retrieval**: Only Top-K documents are retrieved, not the entire knowledge base.
