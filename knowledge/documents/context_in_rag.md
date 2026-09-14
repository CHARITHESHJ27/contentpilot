# Context in RAG

## What is Context?

In RAG, **context** refers to the relevant information retrieved from the knowledge base that is provided to the LLM as part of its input prompt. The LLM uses this context to generate more accurate and grounded responses.

## How Context Works in RAG

1. **Retrieval**: The system searches the knowledge base and retrieves relevant document chunks.
2. **Context formation**: The retrieved chunks are assembled into a context block.
3. **Prompt augmentation**: The context is inserted into the LLM's prompt, typically before the user's question.
4. **Generation**: The LLM reads the context and uses it to inform its response.

## Example Prompt with Context

```
System: You are a helpful assistant. Use the following context to answer the question.

Context:
[Retrieved document chunk 1]
[Retrieved document chunk 2]
[Retrieved document chunk 3]

User: What is machine learning?
```

## Important Principles

### Context is DATA, not instructions
Retrieved content should be treated as **data** for the LLM to reference, NOT as trusted instructions. This is important for security — if malicious content is in the knowledge base, it should not be able to override the system's behavior.

### Bounded context
Only the most relevant documents should be included as context. Sending too much context:
- Increases cost (more tokens = more expense)
- Can confuse the LLM (irrelevant information dilutes relevant information)
- May exceed the LLM's context window limit

### Context window
Every LLM has a maximum number of tokens it can process at once (its "context window"). RAG must ensure the retrieved context plus the prompt does not exceed this limit.

## Key Point

Context in RAG is the bridge between retrieval and generation. It is how the LLM gets access to external information without being retrained. The LLM's weights are never changed — only its input is enriched with relevant context.
