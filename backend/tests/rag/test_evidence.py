import pytest

from backend.app.rag.evidence import (
    RAGEvidenceBuilder,
)
from backend.app.rag.models import (
    DocumentChunk,
    RetrievedChunk,
)


def make_retrieved_chunk(
    *,
    chunk_id: str,
    document_id: str,
    text: str,
    chunk_index: int,
    score: float,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            text=text,
            chunk_index=chunk_index,
            metadata={
                "manufacturer": "Texas Instruments",
                "mpn": "LM358",
            },
        ),
        score=score,
        metadata={
            "collection": "bom_documents",
            "reranked": True,
        },
    )


@pytest.fixture
def builder() -> RAGEvidenceBuilder:
    return RAGEvidenceBuilder()


def test_builds_evidence_from_retrieved_chunk(
    builder: RAGEvidenceBuilder,
):
    chunk = make_retrieved_chunk(
        chunk_id="DOC-001-chunk-0",
        document_id="DOC-001",
        text="LM358 operational amplifier specifications.",
        chunk_index=0,
        score=0.94,
    )

    evidence = builder.build(
        [chunk]
    )

    assert len(evidence) == 1

    result = evidence[0]

    assert result.source == "rag"
    assert result.source_id == "DOC-001"

    assert (
        result.excerpt
        == "LM358 operational amplifier specifications."
    )


def test_preserves_chunk_identity(
    builder: RAGEvidenceBuilder,
):
    chunk = make_retrieved_chunk(
        chunk_id="DOC-001-chunk-3",
        document_id="DOC-001",
        text="Operating temperature range.",
        chunk_index=3,
        score=0.87,
    )

    evidence = builder.build(
        [chunk]
    )[0]

    assert (
        evidence.metadata["document_id"]
        == "DOC-001"
    )

    assert (
        evidence.metadata["chunk_id"]
        == "DOC-001-chunk-3"
    )

    assert (
        evidence.metadata["chunk_index"]
        == 3
    )


def test_preserves_retrieval_score(
    builder: RAGEvidenceBuilder,
):
    chunk = make_retrieved_chunk(
        chunk_id="DOC-001-chunk-0",
        document_id="DOC-001",
        text="Voltage information.",
        chunk_index=0,
        score=0.9125,
    )

    evidence = builder.build(
        [chunk]
    )[0]

    assert (
        evidence.metadata["score"]
        == 0.9125
    )


def test_preserves_chunk_metadata(
    builder: RAGEvidenceBuilder,
):
    chunk = make_retrieved_chunk(
        chunk_id="DOC-001-chunk-0",
        document_id="DOC-001",
        text="LM358 information.",
        chunk_index=0,
        score=0.9,
    )

    evidence = builder.build(
        [chunk]
    )[0]

    assert (
        evidence.metadata["chunk_metadata"][
            "manufacturer"
        ]
        == "Texas Instruments"
    )

    assert (
        evidence.metadata["chunk_metadata"][
            "mpn"
        ]
        == "LM358"
    )


def test_preserves_retrieval_metadata(
    builder: RAGEvidenceBuilder,
):
    chunk = make_retrieved_chunk(
        chunk_id="DOC-001-chunk-0",
        document_id="DOC-001",
        text="LM358 information.",
        chunk_index=0,
        score=0.9,
    )

    evidence = builder.build(
        [chunk]
    )[0]

    assert (
        evidence.metadata[
            "retrieval_metadata"
        ]["collection"]
        == "bom_documents"
    )

    assert (
        evidence.metadata[
            "retrieval_metadata"
        ]["reranked"]
        is True
    )


def test_builds_multiple_evidence_items(
    builder: RAGEvidenceBuilder,
):
    chunks = [
        make_retrieved_chunk(
            chunk_id="DOC-001-chunk-0",
            document_id="DOC-001",
            text="First source.",
            chunk_index=0,
            score=0.95,
        ),
        make_retrieved_chunk(
            chunk_id="DOC-001-chunk-1",
            document_id="DOC-001",
            text="Second source.",
            chunk_index=1,
            score=0.88,
        ),
    ]

    evidence = builder.build(
        chunks
    )

    assert len(evidence) == 2

    assert (
        evidence[0].metadata["chunk_id"]
        == "DOC-001-chunk-0"
    )

    assert (
        evidence[1].metadata["chunk_id"]
        == "DOC-001-chunk-1"
    )


def test_build_respects_limit(
    builder: RAGEvidenceBuilder,
):
    chunks = [
        make_retrieved_chunk(
            chunk_id="chunk-0",
            document_id="DOC-001",
            text="First.",
            chunk_index=0,
            score=0.95,
        ),
        make_retrieved_chunk(
            chunk_id="chunk-1",
            document_id="DOC-001",
            text="Second.",
            chunk_index=1,
            score=0.90,
        ),
        make_retrieved_chunk(
            chunk_id="chunk-2",
            document_id="DOC-001",
            text="Third.",
            chunk_index=2,
            score=0.85,
        ),
    ]

    evidence = builder.build(
        chunks,
        limit=2,
    )

    assert len(evidence) == 2

    assert (
        evidence[0].metadata["chunk_id"]
        == "chunk-0"
    )

    assert (
        evidence[1].metadata["chunk_id"]
        == "chunk-1"
    )


def test_empty_chunks_return_empty_evidence(
    builder: RAGEvidenceBuilder,
):
    evidence = builder.build([])

    assert evidence == []


def test_zero_limit_is_rejected(
    builder: RAGEvidenceBuilder,
):
    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        builder.build(
            [],
            limit=0,
        )