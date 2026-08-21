# RAG

The RAG module provides document chunking, embedding,
vector indexing, retrieval, reranking, and evidence
generation for the BOM Intelligence Agent.

## Pipeline

Documents
-> chunking
-> embeddings
-> Qdrant
-> retrieval
-> reranking
-> evidence
-> agent

## Components

- `models.py`
  - Document models
  - Document chunk models
  - Retrieved chunk models

- `chunking.py`
  - Deterministic overlapping character-based chunking

- `embeddings.py`
  - Provider-agnostic embedding interface
  - Deterministic test provider
  - OpenAI embedding provider

- `embedding_factory.py`
  - Configurable embedding provider construction

- `indexer.py`
  - Embeds document chunks
  - Persists vectors through the vector-store abstraction

- `document_service.py`
  - Coordinates document chunking and indexing

- `vector_store.py`
  - Qdrant-backed vector persistence
  - Vector dimension validation
  - Similarity search

- `retriever.py`
  - Embeds retrieval queries
  - Retrieves relevant document chunks

- `reranker.py`
  - Reranks retrieved chunks

- `evidence.py`
  - Converts retrieved chunks into standardized agent evidence

- `service.py`
  - Orchestrates retrieval, reranking, and evidence generation

- `initialization.py`
  - Initializes and validates the application Qdrant collection

## Embedding Providers

The system supports:

- `deterministic`
  - Used for development and tests
  - No external API dependency

- `openai`
  - Production semantic embeddings
  - Configured through environment variables

## Configuration

```env
EMBEDDING_PROVIDER=deterministic
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=
```
