from pathlib import Path

import fitz
import pytest
from qdrant_client import QdrantClient

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.documents.pdf import PDFDocumentLoader
from backend.app.rag.documents.service import (
    DocumentIngestionService,
)
from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.rag.indexer import RAGIndexer
from backend.app.rag.retriever import RAGRetriever
from backend.app.rag.vector_store import QdrantVectorStore


def create_datasheet_pdf(
    file_path: Path,
) -> None:
    """
    Create a small multi-page engineering datasheet
    for ingestion-service integration testing.
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

        document.save(file_path)
    finally:
        document.close()


@pytest.mark.asyncio
async def test_real_pdf_ingestion_service_indexes_document(
    tmp_path: Path,
) -> None:
    pdf_path = (
        tmp_path / "ACME-REG-001_datasheet.pdf"
    )

    create_datasheet_pdf(pdf_path)

    client = QdrantClient(
        location=":memory:",
    )

    embedding_provider = (
        DeterministicEmbeddingProvider(
            dimension=8,
        )
    )

    vector_store = QdrantVectorStore(
        client,
        collection_name="test_document_ingestion",
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

    result = await service.ingest(
        file_path=pdf_path,
    )

    assert result["source"] == (
        "ACME-REG-001_datasheet.pdf"
    )

    assert result["pages_processed"] == 3

    assert result["chunks_created"] == 3

    assert result["chunks_indexed"] == 3

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
        item
        for item in results
        if (
            "Input voltage range: "
            "4.5 V to 5.5 V."
            in item.chunk.text
        )
    ]

    assert len(matching_results) == 1

    matching_result = matching_results[0]

    assert matching_result.chunk.document_id == (
        result["document_id"]
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

@pytest.mark.asyncio
async def test_real_pdf_ingestion_rejects_corrupt_pdf(
    tmp_path: Path,
) -> None:
    pdf_path = (
        tmp_path / "corrupt.pdf"
    )

    pdf_path.write_bytes(
        b"This is not a valid PDF."
    )

    client = QdrantClient(
        location=":memory:",
    )

    embedding_provider = (
        DeterministicEmbeddingProvider(
            dimension=8,
        )
    )

    vector_store = QdrantVectorStore(
        client,
        collection_name="test_corrupt_pdf",
        vector_size=embedding_provider.dimension,
    )

    vector_store.ensure_collection()

    indexer = RAGIndexer(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    service = DocumentIngestionService(
        loader=PDFDocumentLoader(),
        chunker=DocumentChunker(),
        indexer=indexer,
    )

    with pytest.raises(
        RuntimeError,
        match="Unable to open PDF file",
    ):
        await service.ingest(
            file_path=pdf_path,
        )

@pytest.mark.asyncio
async def test_reingesting_same_pdf_is_idempotent(
    tmp_path: Path,
) -> None:
    pdf_path = (
        tmp_path / "ACME-REG-001_datasheet.pdf"
    )

    create_datasheet_pdf(pdf_path)

    client = QdrantClient(
        location=":memory:",
    )

    embedding_provider = (
        DeterministicEmbeddingProvider(
            dimension=8,
        )
    )

    vector_store = QdrantVectorStore(
        client,
        collection_name="test_idempotent_ingestion",
        vector_size=embedding_provider.dimension,
    )

    vector_store.ensure_collection()

    indexer = RAGIndexer(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    service = DocumentIngestionService(
        loader=PDFDocumentLoader(),
        chunker=DocumentChunker(
            chunk_size=1000,
            chunk_overlap=0,
        ),
        indexer=indexer,
    )

    first_result = await service.ingest(
        file_path=pdf_path,
    )

    second_result = await service.ingest(
        file_path=pdf_path,
    )

    assert second_result["document_id"] == (
        first_result["document_id"]
    )

    assert second_result["source"] == (
        first_result["source"]
    )

    assert second_result["pages_processed"] == (
        first_result["pages_processed"]
    )

    assert second_result["chunks_created"] == (
        first_result["chunks_created"]
    )

    assert second_result["chunks_indexed"] == (
        first_result["chunks_indexed"]
    )

    collection_count = client.count(
        collection_name=(
            "test_idempotent_ingestion"
        ),
    ).count

    assert collection_count == (
        first_result["chunks_created"]
    )