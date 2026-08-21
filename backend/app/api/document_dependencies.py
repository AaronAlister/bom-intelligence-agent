from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.documents.pdf import PDFDocumentLoader
from backend.app.rag.documents.persistence import (
    DocumentIngestionPersistence,
)
from backend.app.rag.documents.service import (
    DocumentIngestionService,
)
from backend.app.rag.embedding_factory import (
    build_embedding_provider,
)
from backend.app.rag.indexer import RAGIndexer
from backend.app.rag.vector_store import QdrantVectorStore


def get_document_ingestion_service(
    request: Request,
    db_session: AsyncSession = Depends(get_db),
) -> DocumentIngestionService:
    """
    Build the engineering document ingestion service
    using the application's initialized RAG vector store
    and database session.
    """

    vector_store = request.app.state.rag_vector_store

    if not isinstance(
        vector_store,
        QdrantVectorStore,
    ):
        raise RuntimeError(
            "Application RAG vector store is not initialized."
        )

    from backend.app.core.config import settings

    embedding_provider = build_embedding_provider(
        provider=settings.embedding_provider,
        dimension=settings.embedding_dimension,
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )

    indexer = RAGIndexer(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    persistence = DocumentIngestionPersistence(
        db_session
    )

    return DocumentIngestionService(
        loader=PDFDocumentLoader(),
        chunker=DocumentChunker(
            chunk_size=1000,
            chunk_overlap=200,
        ),
        indexer=indexer,
        persistence=persistence,
    )