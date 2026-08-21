from typing import Any
from uuid import UUID, NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from backend.app.rag.models import (
    DocumentChunk,
    RetrievedChunk,
)


class QdrantVectorStore:
    """
    Qdrant-backed vector repository for document chunks.

    The repository owns vector persistence and retrieval.
    Embedding generation remains the responsibility of the
    embedding provider.
    """

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        vector_size: int,
    ) -> None:
        if not collection_name.strip():
            raise ValueError(
                "collection_name cannot be empty."
            )

        if vector_size <= 0:
            raise ValueError(
                "vector_size must be greater than zero."
            )

        self._client = client
        self.collection_name = collection_name
        self.vector_size = vector_size

    def ensure_collection(self) -> None:
        """
        Create the collection if it does not exist.

        If the collection already exists, validate that its
        configured vector dimension matches this vector store.
        """

        if not self._client.collection_exists(
            self.collection_name
        ):
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            return

        collection = self._client.get_collection(
            self.collection_name
        )

        vectors_config = collection.config.params.vectors

        if isinstance(vectors_config, dict):
            vector_config = vectors_config.get("")
        else:
            vector_config = vectors_config

        if vector_config is None:
            raise ValueError(
                "Unable to determine vector configuration for "
                f"Qdrant collection '{self.collection_name}'."
            )

        existing_size = vector_config.size

        if existing_size != self.vector_size:
            raise ValueError(
                "Qdrant collection vector dimension mismatch: "
                f"collection '{self.collection_name}' uses "
                f"{existing_size} dimensions, but the configured "
                f"embedding provider uses {self.vector_size}."
            )

    def upsert(
        self,
        *,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        """
        Store document chunks and their embeddings.

        Exactly one vector must be supplied for every chunk.
        """

        if len(chunks) != len(vectors):
            raise ValueError(
                "chunks and vectors must contain "
                "the same number of items."
            )

        if not chunks:
            return

        points: list[PointStruct] = []

        for chunk, vector in zip(
            chunks,
            vectors,
            strict=True,
        ):
            self._validate_vector(vector)

            points.append(
                PointStruct(
                    id=self._point_id(chunk.chunk_id),
                    vector=vector,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "text": chunk.text,
                        "chunk_index": chunk.chunk_index,
                        "metadata": chunk.metadata,
                    },
                )
            )

        self._client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def search(
        self,
        *,
        vector: list[float],
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Search Qdrant for the most relevant document chunks.
        """

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        self._validate_vector(vector)

        results = self._client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
        ).points

        retrieved: list[RetrievedChunk] = []

        for result in results:
            payload: dict[str, Any] = (
                result.payload or {}
            )

            chunk = DocumentChunk(
                chunk_id=payload["chunk_id"],
                document_id=payload["document_id"],
                text=payload["text"],
                chunk_index=payload["chunk_index"],
                metadata=payload.get(
                    "metadata",
                    {},
                ),
            )

            retrieved.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=float(result.score),
                    metadata={
                        "collection": (
                            self.collection_name
                        ),
                    },
                )
            )

        return retrieved

    @staticmethod
    def _point_id(chunk_id: str) -> UUID:
        """
        Convert the application chunk ID into a deterministic
        UUID accepted by Qdrant.
        """

        return uuid5(
            NAMESPACE_URL,
            f"bom-intelligence:{chunk_id}",
        )

    def _validate_vector(
        self,
        vector: list[float],
    ) -> None:
        if len(vector) != self.vector_size:
            raise ValueError(
                "Vector dimension does not match "
                f"collection dimension "
                f"{self.vector_size}."
            )