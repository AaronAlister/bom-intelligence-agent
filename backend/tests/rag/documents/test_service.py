from pathlib import Path

import pytest

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.documents.models import (
    ParsedDocument,
    ParsedPage,
)
from backend.app.rag.documents.service import (
    DocumentIngestionService,
)
from backend.app.rag.models import (
    Document,
    DocumentChunk,
)


class FakeLoader:
    def __init__(
        self,
        parsed_document: ParsedDocument,
    ) -> None:
        self.parsed_document = parsed_document
        self.received_path: Path | None = None

    def load(
        self,
        file_path: Path,
    ) -> ParsedDocument:
        self.received_path = file_path
        return self.parsed_document


class FakeIndexer:
    def __init__(self) -> None:
        self.received_chunks: list[
            DocumentChunk
        ] = []

    async def index(
        self,
        *,
        chunks: list[DocumentChunk],
    ) -> int:
        self.received_chunks = chunks
        return len(chunks)


class FakePersistence:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    async def record_success(
        self,
        *,
        document_id: str,
        source_file: str,
        source_format: str,
        pages_processed: int,
        chunks_created: int,
        chunks_indexed: int,
    ) -> None:
        self.records.append(
            {
                "document_id": document_id,
                "source_file": source_file,
                "source_format": source_format,
                "pages_processed": pages_processed,
                "chunks_created": chunks_created,
                "chunks_indexed": chunks_indexed,
            }
        )


def make_parsed_document() -> ParsedDocument:
    document = Document(
        document_id="DOC-INGEST-001",
        title="Engineering Datasheet",
        source="test-datasheet.pdf",
        manufacturer="Acme",
        mpn="ACME-001",
        metadata={
            "document_type": "pdf",
        },
    )

    return ParsedDocument(
        document=document,
        pages=[
            ParsedPage(
                page_number=1,
                text="Product overview.",
            ),
            ParsedPage(
                page_number=2,
                text=(
                    "Input voltage range: "
                    "3 V to 36 V."
                ),
            ),
        ],
    )


@pytest.mark.asyncio
async def test_ingest_loads_chunks_and_indexes_document(
    tmp_path: Path,
) -> None:
    parsed_document = make_parsed_document()

    loader = FakeLoader(
        parsed_document
    )

    indexer = FakeIndexer()

    service = DocumentIngestionService(
        loader=loader,
        chunker=DocumentChunker(
            chunk_size=100,
            chunk_overlap=0,
        ),
        indexer=indexer,
    )

    file_path = (
        tmp_path / "test-datasheet.pdf"
    )

    result = await service.ingest(
        file_path=file_path
    )

    assert loader.received_path == file_path

    assert result["document_id"] == (
        "DOC-INGEST-001"
    )

    assert result["source"] == (
        "test-datasheet.pdf"
    )

    assert result["pages_processed"] == 2

    assert result["chunks_created"] == 2

    assert result["chunks_indexed"] == 2

    assert len(indexer.received_chunks) == 2


@pytest.mark.asyncio
async def test_ingest_preserves_page_provenance(
    tmp_path: Path,
) -> None:
    parsed_document = make_parsed_document()

    loader = FakeLoader(
        parsed_document
    )

    indexer = FakeIndexer()

    service = DocumentIngestionService(
        loader=loader,
        chunker=DocumentChunker(
            chunk_size=100,
            chunk_overlap=0,
        ),
        indexer=indexer,
    )

    file_path = (
        tmp_path / "test-datasheet.pdf"
    )

    await service.ingest(
        file_path=file_path
    )

    assert len(indexer.received_chunks) == 2

    first_chunk = (
        indexer.received_chunks[0]
    )

    second_chunk = (
        indexer.received_chunks[1]
    )

    assert first_chunk.metadata[
        "page_number"
    ] == 1

    assert second_chunk.metadata[
        "page_number"
    ] == 2


@pytest.mark.asyncio
async def test_ingest_preserves_document_metadata(
    tmp_path: Path,
) -> None:
    parsed_document = make_parsed_document()

    loader = FakeLoader(
        parsed_document
    )

    indexer = FakeIndexer()

    service = DocumentIngestionService(
        loader=loader,
        chunker=DocumentChunker(),
        indexer=indexer,
    )

    await service.ingest(
        file_path=(
            tmp_path / "test-datasheet.pdf"
        ),
    )

    assert len(indexer.received_chunks) == 2

    metadata = (
        indexer.received_chunks[0].metadata
    )

    assert metadata["manufacturer"] == (
        "Acme"
    )

    assert metadata["mpn"] == "ACME-001"

    assert metadata["source"] == (
        "test-datasheet.pdf"
    )

    assert metadata["document_type"] == "pdf"


@pytest.mark.asyncio
async def test_ingest_rejects_document_with_zero_chunks(
    tmp_path: Path,
) -> None:
    document = Document(
        document_id="DOC-EMPTY-001",
        title="Empty Datasheet",
        source="empty.pdf",
    )

    parsed_document = ParsedDocument(
        document=document,
        pages=[
            ParsedPage(
                page_number=1,
                text="",
            ),
            ParsedPage(
                page_number=2,
                text="   ",
            ),
        ],
    )

    loader = FakeLoader(
        parsed_document
    )

    indexer = FakeIndexer()

    service = DocumentIngestionService(
        loader=loader,
        chunker=DocumentChunker(),
        indexer=indexer,
    )

    with pytest.raises(
        ValueError,
        match="No searchable content found",
    ):
        await service.ingest(
            file_path=(
                tmp_path / "empty.pdf"
            ),
        )

    assert indexer.received_chunks == []

@pytest.mark.asyncio
async def test_ingest_propagates_loader_failure(
    tmp_path: Path,
) -> None:
    class FailingLoader:
        def load(
            self,
            file_path: Path,
        ) -> ParsedDocument:
            raise RuntimeError(
                "Unable to extract document."
            )

    indexer = FakeIndexer()

    service = DocumentIngestionService(
        loader=FailingLoader(),
        chunker=DocumentChunker(),
        indexer=indexer,
    )

    with pytest.raises(
        RuntimeError,
        match="Unable to extract document",
    ):
        await service.ingest(
            file_path=(
                tmp_path / "broken.pdf"
            ),
        )

    assert indexer.received_chunks == []


@pytest.mark.asyncio
async def test_ingest_propagates_indexing_failure(
    tmp_path: Path,
) -> None:
    class FailingIndexer:
        async def index(
            self,
            *,
            chunks: list[DocumentChunk],
        ) -> int:
            raise RuntimeError(
                "Vector indexing failed."
            )

    service = DocumentIngestionService(
        loader=FakeLoader(
            make_parsed_document()
        ),
        chunker=DocumentChunker(),
        indexer=FailingIndexer(),
    )

    with pytest.raises(
        RuntimeError,
        match="Vector indexing failed",
    ):
        await service.ingest(
            file_path=(
                tmp_path / "test-datasheet.pdf"
            ),
        )


@pytest.mark.asyncio
async def test_ingest_rejects_document_with_no_chunks(
    tmp_path: Path,
) -> None:
    document = Document(
        document_id="DOC-NO-CHUNKS",
        title="Empty Datasheet",
        source="empty.pdf",
    )

    parsed_document = ParsedDocument(
        document=document,
        pages=[
            ParsedPage(
                page_number=1,
                text="",
            ),
            ParsedPage(
                page_number=2,
                text="   ",
            ),
        ],
    )

    service = DocumentIngestionService(
        loader=FakeLoader(
            parsed_document
        ),
        chunker=DocumentChunker(),
        indexer=FakeIndexer(),
    )

    with pytest.raises(
        ValueError,
        match="No searchable content",
    ):
        await service.ingest(
            file_path=(
                tmp_path / "empty.pdf"
            ),
        )


@pytest.mark.asyncio
async def test_ingest_persists_successful_ingestion(
    tmp_path: Path,
) -> None:
    persistence = FakePersistence()

    service = DocumentIngestionService(
        loader=FakeLoader(
            make_parsed_document()
        ),
        chunker=DocumentChunker(
            chunk_size=100,
            chunk_overlap=0,
        ),
        indexer=FakeIndexer(),
        persistence=persistence,
    )

    result = await service.ingest(
        file_path=(
            tmp_path / "test-datasheet.pdf"
        ),
    )

    assert result["chunks_indexed"] == 2

    assert persistence.records == [
        {
            "document_id": "DOC-INGEST-001",
            "source_file": "test-datasheet.pdf",
            "source_format": "pdf",
            "pages_processed": 2,
            "chunks_created": 2,
            "chunks_indexed": 2,
        }
    ]