from pathlib import Path

import fitz
import pytest
from qdrant_client import QdrantClient

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.documents.pdf import PDFDocumentLoader
from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.rag.evidence import RAGEvidenceBuilder
from backend.app.rag.indexer import RAGIndexer
from backend.app.rag.reranker import RAGReranker
from backend.app.rag.retriever import RAGRetriever
from backend.app.rag.service import RAGService
from backend.app.rag.vector_store import QdrantVectorStore


def create_datasheet_pdf(
    file_path: Path,
) -> None:
    """
    Create a small multi-page engineering datasheet
    for end-to-end ingestion testing.
    """

    document = fitz.open()

    try:
        page_one = document.new_page()

        page_one.insert_text(
            (72, 72),
            "TPS7A4901 Datasheet\n"
            "Product Overview\n"
            "Low-noise linear regulator.",
        )

        page_two = document.new_page()

        page_two.insert_text(
            (72, 72),
            "TPS7A4901 Electrical Characteristics\n"
            "Input voltage range: 3 V to 36 V.\n"
            "Maximum output current: 300 mA.",
        )

        page_three = document.new_page()

        page_three.insert_text(
            (72, 72),
            "TPS7A4901 Operating Conditions\n"
            "Operating temperature: -40 C to 125 C.",
        )

        document.save(file_path)
    finally:
        document.close()


@pytest.mark.asyncio
async def test_pdf_to_rag_evidence_preserves_page_provenance(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "TPS7A4901_datasheet.pdf"

    create_datasheet_pdf(pdf_path)

    loader = PDFDocumentLoader()

    parsed_document = loader.load(pdf_path)

    assert len(parsed_document.pages) == 3

    assert parsed_document.pages[1].page_number == 2

    assert (
        "Input voltage range: 3 V to 36 V."
        in parsed_document.pages[1].text
    )

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=0,
    )

    chunks = chunker.chunk_parsed_document(
        parsed_document,
    )

    assert len(chunks) == 3

    page_numbers = [
        chunk.metadata["page_number"]
        for chunk in chunks
    ]

    assert page_numbers == [1, 2, 3]

    client = QdrantClient(
        location=":memory:",
    )

    embedding_provider = DeterministicEmbeddingProvider(
        dimension=8,
    )

    vector_store = QdrantVectorStore(
        client,
        collection_name="test_pdf_rag",
        vector_size=embedding_provider.dimension,
    )

    vector_store.ensure_collection()

    indexer = RAGIndexer(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    indexed_count = await indexer.index(
        chunks=chunks,
    )

    assert indexed_count == len(chunks)

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    rag_service = RAGService(
        retriever=retriever,
        reranker=RAGReranker(),
        evidence_builder=RAGEvidenceBuilder(),
    )

    evidence = await rag_service.retrieve_evidence(
        query="Input voltage range: 3 V to 36 V.",
        retrieval_limit=3,
        evidence_limit=1,
    )

    assert len(evidence) == 1

    result = evidence[0]

    assert result.source == "rag"

    assert result.source_id == (
        parsed_document.document.document_id
    )
     
    assert result.excerpt is not None

    assert (
        "Input voltage range: 3 V to 36 V."
        in result.excerpt
    )

    chunk_metadata = result.metadata[
        "chunk_metadata"
    ]

    assert chunk_metadata["page_number"] == 2

    assert chunk_metadata["source"] == (
        "TPS7A4901_datasheet.pdf"
    )

    assert chunk_metadata["document_type"] == "pdf"