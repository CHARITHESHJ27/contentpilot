# Retrieval Basics in RAG

## What is Retrieval?

Retrieval is the process of finding and fetching relevant information from a collection of documents based on a query. In the context of RAG, retrieval means searching a knowledge base to find documents or passages that are relevant to the user's question.

## The Retrieval Process

1. **User asks a question**: The user submits a query (e.g., "What is machine learning?").
2. **Query processing**: The query is processed and possibly reformulated to improve search results.
3. **Search**: The system searches through the knowledge base to find relevant documents or passages.
4. **Ranking**: The retrieved results are ranked by relevance to the query.
5. **Selection**: The top-K most relevant results are selected (K is typically 3-10).
6. **Context formation**: The selected documents are formatted as context for the LLM.

## Types of Retrieval

### Keyword-Based Retrieval
- Searches for exact word matches
- Fast but misses semantic similarities
- Example: BM25 algorithm

### Semantic Retrieval
- Uses embeddings to understand meaning
- Can find relevant documents even without exact word matches
- Example: Dense vector search in a vector database

### Hybrid Retrieval
- Combines keyword and semantic approaches
- Often provides the best results
- More complex to implement

## Important Concepts

- **Top-K**: The number of documents retrieved. A configurable parameter, typically between 3 and 10.
- **Relevance score**: A numerical measure of how relevant a document is to the query.
- **Re-ranking**: A second pass that re-orders retrieved documents using a more sophisticated model.
- **Query expansion**: Techniques to improve the query before searching (e.g., adding synonyms).

## Key Principle

Retrieval in RAG should be **bounded** — only the most relevant documents should be sent to the LLM, not the entire knowledge base. This keeps the context focused and reduces costs.
