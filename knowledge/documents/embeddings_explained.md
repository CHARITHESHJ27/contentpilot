# Embeddings Explained

## What are Embeddings?

Embeddings are **numerical representations** (vectors) of text. They convert words, sentences, or entire documents into lists of numbers that capture the **meaning** of the text.

## Simple Analogy

Think of embeddings like GPS coordinates for meaning. Just as GPS coordinates (latitude, longitude) represent a physical location, embeddings represent the "location" of a piece of text in a "meaning space." Texts with similar meanings will have coordinates that are close together.

## How Embeddings Work

1. **Input**: A piece of text (word, sentence, paragraph, or document).
2. **Embedding model**: A specialized neural network processes the text.
3. **Output**: A vector (list of numbers), typically with 256 to 3072 dimensions.

Example:
- "dog" → [0.23, -0.45, 0.67, 0.12, ...]
- "puppy" → [0.25, -0.43, 0.65, 0.14, ...] (similar to "dog")
- "car" → [-0.56, 0.78, -0.23, 0.89, ...] (very different from "dog")

## Why Embeddings Matter for RAG

In RAG, embeddings are used to:

1. **Index documents**: Each document chunk is converted into an embedding and stored in a vector database.
2. **Search for relevant documents**: The user's query is also converted into an embedding, and the system finds document chunks whose embeddings are closest to the query embedding.
3. **Measure similarity**: The distance between two embeddings indicates how semantically similar two pieces of text are.

## Embedding Models

Common embedding models include:
- OpenAI's text-embedding-3-small and text-embedding-3-large
- Sentence Transformers (open-source)
- Cohere Embed

## Key Points

- Embeddings capture **semantic meaning**, not just keywords.
- Similar texts produce **similar embeddings** (close in vector space).
- Embeddings enable **semantic search** — finding relevant content based on meaning rather than exact word matching.
- Embedding models are **separate** from the LLM used for generation.
