from pathlib import Path

import fitz
import pytest
from httpx import ASGITransport, AsyncClient
from qdrant_client import QdrantClient

from backend.app.api.document_dependencies import (
    get_document_ingestion_service,
)
from backend.app.main import app
from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.documents.pdf import (
    PDFDocumentLoader,
)
from backend.app.rag.documents.service import (
    DocumentIngestionService,
)
from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.rag.indexer import RAGIndexer
from backend.app.rag.retriever import RAGRetriever
from backend.app.rag.vector_store import (
    QdrantVectorStore,
)


BASE_URL = "http://test"


def create_e2e_datasheet() -> bytes:
    """
    Create a small multi-page engineering datasheet
    entirely in memory for API E2E testing.
    """

    document = fitz.open()

    try:
        page_one = document.new_page()

        page_one.insert_text(
            (72, 72),
            "ACME-REG-001 Datasheet\n"
            "Product Overview\n"
            "Low-noise voltage regulator.",
        )

        page_two = document.new_page()

        page_two.insert_text(
            (72, 72),
            "Electrical Characteristics\n"
            "Input voltage range: 4.5 V to 5.5 V.\n"
            "Maximum output current: 300 mA.",
        )

        page_three = document.new_page()

        page_three.insert_text(
            (72, 72),
            "Operating Conditions\n"
            "Operating temperature: -40 C to 125 C.",
        )

        return document.tobytes()

    finally:
        document.close()


def build_test_ingestion_service() -> tuple[
    DocumentIngestionService,
    DeterministicEmbeddingProvider,
    QdrantVectorStore,
]:
    """
    Build a completely isolated ingestion stack for
    the API E2E test.

    No external Qdrant or OpenAI service is used.
    """

    embedding_provider = (
        DeterministicEmbeddingProvider(
            dimension=8,
        )
    )

    qdrant_client = QdrantClient(
        location=":memory:",
    )

    vector_store = QdrantVectorStore(
        qdrant_client,
        collection_name="test_api_document_e2e",
        vector_size=embedding_provider.dimension,
    )

    vector_store.ensure_collection()

    indexer = RAGIndexer(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    loader = PDFDocumentLoader()

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=0,
    )

    service = DocumentIngestionService(
        loader=loader,
        chunker=chunker,
        indexer=indexer,
    )

    return (
        service,
        embedding_provider,
        vector_store,
    )


@pytest.mark.asyncio
async def test_document_upload_api_indexes_pdf_and_supports_retrieval():
    (
        ingestion_service,
        embedding_provider,
        vector_store,
    ) = build_test_ingestion_service()

    def override_document_ingestion_service(
    ) -> DocumentIngestionService:
        return ingestion_service

    app.dependency_overrides[
        get_document_ingestion_service
    ] = override_document_ingestion_service

    pdf_bytes = create_e2e_datasheet()

    try:
        transport = ASGITransport(
            app=app,
        )

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "ACME-REG-001_datasheet.pdf",
                        pdf_bytes,
                        "application/pdf",
                    )
                },
            )

        assert response.status_code == 200

        data = response.json()

        assert data["source"] == (
            "ACME-REG-001_datasheet.pdf"
        )

        assert data["pages_processed"] == 3

        assert data["chunks_created"] == 3

        assert data["chunks_indexed"] == 3

        assert data["document_id"].startswith(
            "DOC-"
        )

        retriever = RAGRetriever(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        )

        results = await retriever.retrieve(
            query=(
                "Input voltage range: "
                "4.5 V to 5.5 V."
            ),
            limit=3,
        )

        assert len(results) > 0

        matching_results = [
            result
            for result in results
            if (
                "Input voltage range: "
                "4.5 V to 5.5 V."
                in result.chunk.text
            )
        ]

        assert len(matching_results) == 1

        matching_result = matching_results[0]

        assert (
            matching_result.chunk.document_id
            == data["document_id"]
        )

        assert matching_result.chunk.metadata[
            "page_number"
        ] == 2

        assert matching_result.chunk.metadata[
            "source"
        ] == "ACME-REG-001_datasheet.pdf"

        assert matching_result.chunk.metadata[
            "document_type"
        ] == "pdf"

    finally:
        app.dependency_overrides.pop(
            get_document_ingestion_service,
            None,
        )