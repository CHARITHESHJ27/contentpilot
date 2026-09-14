# Vector Databases

## What is a Vector Database?

A vector database is a specialized database designed to store, index, and search **embedding vectors** efficiently. Unlike traditional databases that search by exact matches or keywords, vector databases find data based on **similarity** in meaning.

## Why Vector Databases for RAG?

In RAG, we need to quickly find documents that are semantically similar to a user's question. Traditional databases are not built for this type of search. Vector databases are specifically designed for:

1. **Storing embeddings**: Each document chunk's embedding (a list of numbers) is stored alongside its metadata.
2. **Fast similarity search**: Given a query embedding, the database quickly finds the most similar document embeddings.
3. **Scalability**: They can handle millions or billions of vectors efficiently.

## How Vector Databases Work

1. **Indexing**: When documents are added, their embeddings are indexed using algorithms like HNSW (Hierarchical Navigable Small World) for fast approximate search.
2. **Querying**: When a query arrives, its embedding is compared against indexed embeddings using distance metrics.
3. **Returning results**: The database returns the Top-K most similar vectors along with their associated metadata and content.

## Distance Metrics

Common ways to measure similarity between vectors:
- **Cosine similarity**: Measures the angle between two vectors. Most commonly used.
- **Euclidean distance**: Measures the straight-line distance between two points.
- **Dot product**: Measures the projection of one vector onto another.

## Examples of Vector Databases

- **Qdrant**: Open-source, supports rich metadata filtering, Docker-friendly
- **Pinecone**: Cloud-managed vector database
- **Weaviate**: Open-source with hybrid search
- **Chroma**: Lightweight, good for prototyping
- **FAISS**: Library by Meta for similarity search (not a full database)

## Important Distinction

A vector database is an **index**, not the source of truth. The original documents should be stored separately. The vector database helps you **find** relevant documents quickly, but the canonical content lives in the original document store.

## Metadata Filtering

Modern vector databases support filtering results by metadata (e.g., topic, difficulty level, date) in addition to vector similarity. This allows more precise retrieval.
