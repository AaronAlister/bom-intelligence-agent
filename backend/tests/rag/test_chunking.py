import pytest

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.models import Document


def make_document() -> Document:
    return Document(
        document_id="DOC-001",
        title="Test Datasheet",
        source="datasheet",
        source_url="https://example.com/datasheet.pdf",
        manufacturer="Test Manufacturer",
        mpn="TEST-MPN-001",
        metadata={
            "document_type": "datasheet",
            "revision": "A",
        },
    )


def test_chunker_splits_long_document():
    document = make_document()

    chunker = DocumentChunker(
        chunk_size=10,
        chunk_overlap=2,
    )

    chunks = chunker.chunk(
        document,
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    )

    assert len(chunks) == 3

    assert chunks[0].text == "ABCDEFGHIJ"
    assert chunks[1].text == "IJKLMNOPQR"
    assert chunks[2].text == "QRSTUVWXYZ"

    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[2].chunk_index == 2


def test_chunk_ids_are_deterministic():
    document = make_document()

    chunker = DocumentChunker(
        chunk_size=10,
        chunk_overlap=2,
    )

    chunks = chunker.chunk(
        document,
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    )

    assert chunks[0].chunk_id == (
        "DOC-001-chunk-0"
    )

    assert chunks[1].chunk_id == (
        "DOC-001-chunk-1"
    )

    assert chunks[2].chunk_id == (
        "DOC-001-chunk-2"
    )


def test_short_document_produces_one_chunk():
    document = make_document()

    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = chunker.chunk(
        document,
        "Short datasheet text.",
    )

    assert len(chunks) == 1
    assert chunks[0].text == "Short datasheet text."


def test_empty_document_produces_no_chunks():
    document = make_document()

    chunker = DocumentChunker()

    assert chunker.chunk(
        document,
        "",
    ) == []

    assert chunker.chunk(
        document,
        "   ",
    ) == []


def test_chunk_metadata_is_preserved():
    document = make_document()

    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = chunker.chunk(
        document,
        "Test component datasheet.",
    )

    metadata = chunks[0].metadata

    assert metadata["document_type"] == "datasheet"
    assert metadata["revision"] == "A"
    assert metadata["title"] == "Test Datasheet"
    assert metadata["source"] == "datasheet"
    assert (
        metadata["source_url"]
        == "https://example.com/datasheet.pdf"
    )
    assert metadata["manufacturer"] == "Test Manufacturer"
    assert metadata["mpn"] == "TEST-MPN-001"


def test_whitespace_is_normalized():
    document = make_document()

    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = chunker.chunk(
        document,
        "   Test datasheet text.   ",
    )

    assert len(chunks) == 1
    assert chunks[0].text == "Test datasheet text."


def test_invalid_chunk_size_is_rejected():
    with pytest.raises(
        ValueError,
        match="chunk_size must be greater than zero",
    ):
        DocumentChunker(
            chunk_size=0,
            chunk_overlap=0,
        )


def test_negative_overlap_is_rejected():
    with pytest.raises(
        ValueError,
        match="chunk_overlap cannot be negative",
    ):
        DocumentChunker(
            chunk_size=100,
            chunk_overlap=-1,
        )


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(
        ValueError,
        match=(
            "chunk_overlap must be smaller "
            "than chunk_size"
        ),
    ):
        DocumentChunker(
            chunk_size=100,
            chunk_overlap=100,
        )