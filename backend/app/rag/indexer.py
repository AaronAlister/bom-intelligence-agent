from typing import Protocol

from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.models import DocumentChunk


class VectorStore(Protocol):
    """
    Interface required by the indexing layer.
    """

    def upsert(
        self,
        *,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        ...


class VectorIndexer(Protocol):
    """
    Interface required by document-level RAG orchestration.
    """

    async def index(
        self,
        *,
        chunks: list[DocumentChunk],
    ) -> int:
        ...


class RAGIndexer:
    """
    Coordinates document chunk embedding and persistence.

    The indexer receives prepared DocumentChunk objects,
    generates embeddings, and stores the resulting vectors.
    """

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def index(
        self,
        *,
        chunks: list[DocumentChunk],
    ) -> int:
        """
        Embed and persist document chunks.

        Returns the number of indexed chunks.
        """

        if not chunks:
            return 0

        texts = [
            chunk.text
            for chunk in chunks
        ]

        vectors = await self._embedding_provider.embed(
            texts
        )

        if len(vectors) != len(chunks):
            raise ValueError(
                "Embedding provider must return exactly "
                "one vector for every document chunk."
            )

        self._vector_store.upsert(
            chunks=chunks,
            vectors=vectors,
        )

        return len(chunks)