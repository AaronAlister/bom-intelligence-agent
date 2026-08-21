from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.models import Document
from backend.app.rag.documents.models import (
    ParsedDocument,
    ParsedPage,
)


def create_document() -> Document:
    return Document(
        document_id="DOC-001",
        title="Test Datasheet",
        source="test",
        source_url="https://example.com/datasheet.pdf",
        manufacturer="Test Manufacturer",
        mpn="TEST-MPN-001",
        metadata={
            "document_type": "datasheet",
        },
    )


def test_chunk_pages_preserves_page_number() -> None:
    document = create_document()

    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = chunker.chunk_pages(
        document,
        [
            {
                "page_number": 1,
                "text": "Input voltage is 3 V to 36 V.",
            },
        ],
    )

    assert len(chunks) == 1
    assert chunks[0].metadata["page_number"] == 1


def test_chunk_pages_preserves_document_metadata() -> None:
    document = create_document()

    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = chunker.chunk_pages(
        document,
        [
            {
                "page_number": 4,
                "text": "Output current is 300 mA.",
            },
        ],
    )

    assert len(chunks) == 1

    metadata = chunks[0].metadata

    assert metadata["document_type"] == "datasheet"
    assert metadata["manufacturer"] == "Test Manufacturer"
    assert metadata["mpn"] == "TEST-MPN-001"
    assert metadata["page_number"] == 4


def test_chunk_pages_does_not_merge_different_pages() -> None:
    document = create_document()

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=200,
    )

    chunks = chunker.chunk_pages(
        document,
        [
            {
                "page_number": 7,
                "text": "Maximum input voltage is 36 V.",
            },
            {
                "page_number": 8,
                "text": "Maximum output current is 300 mA.",
            },
        ],
    )

    assert len(chunks) == 2

    assert chunks[0].metadata["page_number"] == 7
    assert chunks[1].metadata["page_number"] == 8


def test_chunk_pages_assigns_global_chunk_indexes() -> None:
    document = create_document()

    chunker = DocumentChunker(
        chunk_size=20,
        chunk_overlap=5,
    )

    chunks = chunker.chunk_pages(
        document,
        [
            {
                "page_number": 1,
                "text": "A" * 40,
            },
            {
                "page_number": 2,
                "text": "B" * 40,
            },
        ],
    )

    indexes = [
        chunk.chunk_index
        for chunk in chunks
    ]

    assert indexes == list(range(len(chunks)))


def test_chunk_pages_skips_empty_pages() -> None:
    document = create_document()

    chunker = DocumentChunker()

    chunks = chunker.chunk_pages(
        document,
        [
            {
                "page_number": 1,
                "text": "",
            },
            {
                "page_number": 2,
                "text": "Valid content.",
            },
        ],
    )

    assert len(chunks) == 1
    assert chunks[0].metadata["page_number"] == 2


def test_chunk_pages_rejects_invalid_page_number() -> None:
    document = create_document()

    chunker = DocumentChunker()

    try:
        chunker.chunk_pages(
            document,
            [
                {
                    "page_number": "1",
                    "text": "Invalid page number.",
                },
            ],
        )
    except ValueError as exc:
        assert str(exc) == (
            "Each page must contain an integer page_number."
        )
    else:
        raise AssertionError(
            "Expected ValueError for invalid page_number."
        )


def test_chunk_pages_rejects_invalid_page_text() -> None:
    document = create_document()

    chunker = DocumentChunker()

    try:
        chunker.chunk_pages(
            document,
            [
                {
                    "page_number": 1,
                    "text": 123,
                },
            ],
        )
    except ValueError as exc:
        assert str(exc) == (
            "Each page must contain string text."
        )
    else:
        raise AssertionError(
            "Expected ValueError for invalid page text."
        )

def test_chunk_parsed_document_preserves_page_provenance() -> None:
    document = create_document()

    parsed_document = ParsedDocument(
        document=document,
        pages=[
            ParsedPage(
                page_number=3,
                text="Input voltage is 3 V to 36 V.",
            ),
        ],
    )

    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = chunker.chunk_parsed_document(
        parsed_document
    )

    assert len(chunks) == 1
    assert chunks[0].metadata["page_number"] == 3
    assert chunks[0].document_id == "DOC-001"


def test_chunk_parsed_document_preserves_page_metadata() -> None:
    document = create_document()

    parsed_document = ParsedDocument(
        document=document,
        pages=[
            ParsedPage(
                page_number=5,
                text="Electrical characteristics.",
                metadata={
                    "section": "Electrical Characteristics",
                },
            ),
        ],
    )

    chunker = DocumentChunker()

    chunks = chunker.chunk_parsed_document(
        parsed_document
    )

    assert len(chunks) == 1

    metadata = chunks[0].metadata

    assert metadata["page_number"] == 5
    assert metadata["section"] == (
        "Electrical Characteristics"
    )


def test_chunk_parsed_document_preserves_page_order() -> None:
    document = create_document()

    parsed_document = ParsedDocument(
        document=document,
        pages=[
            ParsedPage(
                page_number=7,
                text="Maximum input voltage is 36 V.",
            ),
            ParsedPage(
                page_number=8,
                text="Maximum output current is 300 mA.",
            ),
            ParsedPage(
                page_number=9,
                text="Operating temperature is -40 C to 125 C.",
            ),
        ],
    )

    chunker = DocumentChunker()

    chunks = chunker.chunk_parsed_document(
        parsed_document
    )

    page_numbers = [
        chunk.metadata["page_number"]
        for chunk in chunks
    ]

    assert page_numbers == [7, 8, 9]


def test_chunk_parsed_document_skips_empty_pages() -> None:
    document = create_document()

    parsed_document = ParsedDocument(
        document=document,
        pages=[
            ParsedPage(
                page_number=1,
                text="",
            ),
            ParsedPage(
                page_number=2,
                text="Valid content.",
            ),
            ParsedPage(
                page_number=3,
                text="   ",
            ),
        ],
    )

    chunker = DocumentChunker()

    chunks = chunker.chunk_parsed_document(
        parsed_document
    )

    assert len(chunks) == 1
    assert chunks[0].metadata["page_number"] == 2