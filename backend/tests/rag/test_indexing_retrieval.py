import pytest
from qdrant_client import QdrantClient

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.rag.indexer import RAGIndexer
from backend.app.rag.models import Document
from backend.app.rag.retriever import RAGRetriever
from backend.app.rag.vector_store import QdrantVectorStore


@pytest.mark.asyncio
async def test_document_chunking_indexing_and_retrieval():
    client = QdrantClient(
        location=":memory:",
    )

    embedding_provider = DeterministicEmbeddingProvider(
        dimension=8,
    )

    vector_store = QdrantVectorStore(
        client,
        collection_name="test_bom_documents",
        vector_size=embedding_provider.dimension,
    )

    vector_store.ensure_collection()

    chunker = DocumentChunker(
        chunk_size=40,
        chunk_overlap=0,
    )

    document = Document(
        document_id="DOC-001",
        title="Voltage Regulator Datasheet",
        source="test",
        manufacturer="Acme",
        mpn="ACME-VR-001",
    )

    text = (
        "The input voltage range is 4.5V to 5.5V. "
        "The maximum operating temperature is 85C."
    )

    chunks = chunker.chunk(
        document,
        text,
    )

    assert len(chunks) > 1

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

    results = await retriever.retrieve(
        query=chunks[0].text,
        limit=1,
    )

    assert len(results) == 1
    assert results[0].chunk.chunk_id == chunks[0].chunk_id
    assert results[0].chunk.document_id == document.document_id
    assert results[0].chunk.text == chunks[0].text
    assert results[0].score == pytest.approx(1.0)