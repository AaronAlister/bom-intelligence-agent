from backend.app.rag.evidence import RAGEvidenceBuilder
from backend.app.rag.models import (
    DocumentChunk,
    RetrievedChunk,
)


def test_page_provenance_is_preserved_in_evidence() -> None:
    chunk = DocumentChunk(
        chunk_id="DOC-001-chunk-0",
        document_id="DOC-001",
        text="Input voltage is 3 V to 36 V.",
        chunk_index=0,
        metadata={
            "manufacturer": "Texas Instruments",
            "mpn": "TPS7A4901",
            "source": "TPS7A4901-datasheet.pdf",
            "page_number": 8,
        },
    )

    retrieved = RetrievedChunk(
        chunk=chunk,
        score=0.95,
        metadata={
            "collection": "test_documents",
        },
    )

    evidence = RAGEvidenceBuilder().build(
        [retrieved],
    )

    assert len(evidence) == 1

    result = evidence[0]

    assert result.source == "rag"
    assert result.source_id == "DOC-001"
    assert result.excerpt == (
        "Input voltage is 3 V to 36 V."
    )

    chunk_metadata = result.metadata[
        "chunk_metadata"
    ]

    assert chunk_metadata["page_number"] == 8
    assert chunk_metadata["mpn"] == "TPS7A4901"
    assert chunk_metadata["manufacturer"] == (
        "Texas Instruments"
    )
    assert chunk_metadata["source"] == (
        "TPS7A4901-datasheet.pdf"
    )