import pytest

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.document_service import (
    RAGDocumentService,
)
from backend.app.rag.models import (
    Document,
    DocumentChunk,
)


class FakeIndexer:
    def __init__(self) -> None:
        self.received_chunks: list[DocumentChunk] = []

    async def index(
        self,
        *,
        chunks: list[DocumentChunk],
    ) -> int:
        self.received_chunks = chunks
        return len(chunks)


def make_document() -> Document:
    return Document(
        document_id="DOC-001",
        title="Voltage Regulator Datasheet",
        source="test",
        manufacturer="Acme",
        mpn="ACME-VR-001",
    )


@pytest.mark.asyncio
async def test_index_document_chunks_and_indexes_document():
    chunker = DocumentChunker(
        chunk_size=40,
        chunk_overlap=0,
    )

    indexer = FakeIndexer()

    service = RAGDocumentService(
        chunker=chunker,
        indexer=indexer,
    )

    document = make_document()

    text = (
        "The input voltage range is 4.5V to 5.5V. "
        "The maximum operating temperature is 85C."
    )

    result = await service.index_document(
        document=document,
        text=text,
    )

    assert result["document_id"] == "DOC-001"
    assert result["chunks_created"] > 1
    assert result["chunks_indexed"] == result["chunks_created"]

    assert indexer.received_chunks is not None
    assert len(indexer.received_chunks) == (
        result["chunks_created"]
    )


@pytest.mark.asyncio
async def test_index_document_handles_empty_text():
    chunker = DocumentChunker()

    indexer = FakeIndexer()

    service = RAGDocumentService(
        chunker=chunker,
        indexer=indexer,
    )

    document = make_document()

    result = await service.index_document(
        document=document,
        text="   ",
    )

    assert result == {
        "document_id": "DOC-001",
        "chunks_created": 0,
        "chunks_indexed": 0,
    }

    assert indexer.received_chunks == []


@pytest.mark.asyncio
async def test_index_document_preserves_document_metadata():
    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=0,
    )

    indexer = FakeIndexer()

    service = RAGDocumentService(
        chunker=chunker,
        indexer=indexer,
    )

    document = Document(
        document_id="DOC-002",
        title="MOSFET Datasheet",
        source="manufacturer",
        source_url="https://example.com/datasheet",
        manufacturer="Acme Semiconductor",
        mpn="ACME-MOS-001",
        metadata={
            "category": "MOSFET",
            "frequency": "22GHz",
        },
    )

    result = await service.index_document(
        document=document,
        text="Maximum drain voltage is 40V.",
    )

    assert result["document_id"] == "DOC-002"
    assert result["chunks_created"] == 1
    assert result["chunks_indexed"] == 1

    assert indexer.received_chunks is not None

    chunk = indexer.received_chunks[0]

    assert chunk.document_id == "DOC-002"
    assert chunk.metadata["title"] == "MOSFET Datasheet"
    assert chunk.metadata["source"] == "manufacturer"
    assert chunk.metadata["source_url"] == (
        "https://example.com/datasheet"
    )
    assert chunk.metadata["manufacturer"] == (
        "Acme Semiconductor"
    )
    assert chunk.metadata["mpn"] == "ACME-MOS-001"
    assert chunk.metadata["category"] == "MOSFET"
    assert chunk.metadata["frequency"] == "22GHz"
