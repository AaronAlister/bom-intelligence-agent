import pytest
from qdrant_client import QdrantClient

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.document_service import RAGDocumentService
from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.rag.indexer import RAGIndexer
from backend.app.rag.models import Document
from backend.app.rag.retriever import RAGRetriever
from backend.app.rag.vector_store import QdrantVectorStore


@pytest.mark.asyncio
async def test_document_service_indexes_and_retrieves_document():
    client = QdrantClient(
        location=":memory:",
    )

    embedding_provider = DeterministicEmbeddingProvider(
        dimension=8,
    )

    vector_store = QdrantVectorStore(
        client,
        collection_name="test_document_service",
        vector_size=embedding_provider.dimension,
    )

    vector_store.ensure_collection()

    indexer = RAGIndexer(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    chunker = DocumentChunker(
        chunk_size=50,
        chunk_overlap=0,
    )

    service = RAGDocumentService(
        chunker=chunker,
        indexer=indexer,
    )

    document = Document(
        document_id="DOC-INT-001",
        title="Power Supply Datasheet",
        source="integration-test",
        manufacturer="Acme",
        mpn="ACME-PS-001",
        metadata={
            "category": "power",
        },
    )

    text = (
        "The input voltage range is 4.5V to 5.5V. "
        "The maximum output current is 3A. "
        "The operating temperature range is "
        "-40C to 85C."
    )

    result = await service.index_document(
        document=document,
        text=text,
    )

    assert result["document_id"] == "DOC-INT-001"
    assert result["chunks_created"] > 0
    assert (
        result["chunks_indexed"]
        == result["chunks_created"]
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = await retriever.retrieve(
        query="The input voltage range is 4.5V to 5.5V.",
        limit=3,
    )

    assert len(results) > 0

    top_result = results[0]

    assert (
        top_result.chunk.document_id
        == "DOC-INT-001"
    )

    assert (
        top_result.chunk.metadata["manufacturer"]
        == "Acme"
    )

    assert (
        top_result.chunk.metadata["mpn"]
        == "ACME-PS-001"
    )

    assert (
        top_result.chunk.metadata["category"]
        == "power"
    )