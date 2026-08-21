from typing import Protocol

from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.models import RetrievedChunk


class VectorSearchStore(Protocol):
    """
    Interface required by the retrieval layer.

    The retriever does not care whether the backing store
    is Qdrant, an in-memory implementation, or another
    vector database.
    """

    def search(
        self,
        *,
        vector: list[float],
        limit: int,
    ) -> list[RetrievedChunk]:
        ...


class RAGRetriever:
    """
    Retrieves relevant document chunks for a natural-language query.

    Query embedding generation and vector persistence remain
    delegated to their respective abstractions.
    """

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorSearchStore,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def retrieve(
        self,
        *,
        query: str,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Embed the query and retrieve the most relevant chunks.
        """

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "Retrieval query cannot be empty."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        vectors = await self._embedding_provider.embed(
            [normalized_query]
        )

        if len(vectors) != 1:
            raise ValueError(
                "Embedding provider must return exactly "
                "one vector for the retrieval query."
            )

        return self._vector_store.search(
            vector=vectors[0],
            limit=limit,
        )