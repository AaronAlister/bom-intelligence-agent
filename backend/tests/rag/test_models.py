from backend.app.rag.models import (
    Document,
    DocumentChunk,
    RetrievedChunk,
)


def test_document_creation():
    document = Document(
        document_id="DOC-001",
        title="TPS7A Datasheet",
        source="datasheet",
        manufacturer="Texas Instruments",
        mpn="TPS7A4901",
    )

    assert document.document_id == "DOC-001"
    assert document.title == "TPS7A Datasheet"
    assert document.source == "datasheet"
    assert document.manufacturer == "Texas Instruments"
    assert document.mpn == "TPS7A4901"


def test_document_supports_metadata():
    document = Document(
        document_id="DOC-001",
        title="Test Document",
        source="test",
        metadata={
            "document_type": "datasheet",
            "revision": "A",
        },
    )

    assert document.metadata["document_type"] == "datasheet"
    assert document.metadata["revision"] == "A"


def test_document_chunk_creation():
    chunk = DocumentChunk(
        chunk_id="DOC-001-CHUNK-001",
        document_id="DOC-001",
        text="Operating temperature range: -40°C to 125°C.",
        chunk_index=0,
    )

    assert chunk.chunk_id == "DOC-001-CHUNK-001"
    assert chunk.document_id == "DOC-001"
    assert chunk.chunk_index == 0
    assert "Operating temperature" in chunk.text


def test_retrieved_chunk_creation():
    chunk = DocumentChunk(
        chunk_id="DOC-001-CHUNK-001",
        document_id="DOC-001",
        text="Operating temperature range: -40°C to 125°C.",
        chunk_index=0,
    )

    retrieved = RetrievedChunk(
        chunk=chunk,
        score=0.92,
    )

    assert retrieved.chunk.chunk_id == (
        "DOC-001-CHUNK-001"
    )

    assert retrieved.score == 0.92