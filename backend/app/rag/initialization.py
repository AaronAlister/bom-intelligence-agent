from qdrant_client import QdrantClient

from backend.app.core.config import settings
from backend.app.rag.embedding_factory import (
    build_embedding_provider,
)
from backend.app.rag.vector_store import (
    QdrantVectorStore,
)


def initialize_rag_vector_store() -> QdrantVectorStore:
    """
    Initialize the Qdrant vector store for the application.

    The collection is created if missing and its vector
    dimension is validated against the configured embedding
    provider.
    """

    embedding_provider = build_embedding_provider(
        provider=settings.embedding_provider,
        dimension=settings.embedding_dimension,
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )

    client = QdrantClient(
        url=settings.qdrant_url,
    )

    vector_store = QdrantVectorStore(
        client,
        collection_name=settings.qdrant_collection,
        vector_size=embedding_provider.dimension,
    )

    vector_store.ensure_collection()

    return vector_store