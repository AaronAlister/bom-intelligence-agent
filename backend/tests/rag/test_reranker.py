import pytest

from backend.app.rag.models import (
    DocumentChunk,
    RetrievedChunk,
)
from backend.app.rag.reranker import (
    RAGReranker,
)


def make_chunk(
    chunk_id: str,
    text: str,
    score: float,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            document_id="DOC-001",
            text=text,
            chunk_index=0,
            metadata={
                "source": "test",
            },
        ),
        score=score,
        metadata={
            "retrieval": "qdrant",
        },
    )


@pytest.fixture
def reranker() -> RAGReranker:
    return RAGReranker()


def test_reranker_prioritizes_query_overlap(
    reranker: RAGReranker,
):
    chunks = [
        make_chunk(
            "chunk-a",
            "Generic electronic component",
            0.90,
        ),
        make_chunk(
            "chunk-b",
            "LM358 operational amplifier",
            0.80,
        ),
    ]

    results = reranker.rerank(
        query="LM358 operational amplifier",
        chunks=chunks,
        limit=2,
    )

    assert results[0].chunk.chunk_id == "chunk-b"
    assert results[1].chunk.chunk_id == "chunk-a"


def test_reranker_preserves_chunk_data(
    reranker: RAGReranker,
):
    chunk = make_chunk(
        "chunk-001",
        "Voltage regulator information",
        0.91,
    )

    results = reranker.rerank(
        query="voltage regulator",
        chunks=[chunk],
        limit=1,
    )

    assert len(results) == 1

    result = results[0]

    assert result.chunk.chunk_id == "chunk-001"
    assert (
        result.chunk.text
        == "Voltage regulator information"
    )
    assert result.score == 0.91
    assert (
        result.metadata["retrieval"]
        == "qdrant"
    )


def test_reranker_respects_limit(
    reranker: RAGReranker,
):
    chunks = [
        make_chunk(
            "chunk-1",
            "component one",
            0.90,
        ),
        make_chunk(
            "chunk-2",
            "component two",
            0.80,
        ),
        make_chunk(
            "chunk-3",
            "component three",
            0.70,
        ),
    ]

    results = reranker.rerank(
        query="component",
        chunks=chunks,
        limit=2,
    )

    assert len(results) == 2


def test_reranker_returns_empty_for_no_chunks(
    reranker: RAGReranker,
):
    results = reranker.rerank(
        query="component",
        chunks=[],
        limit=5,
    )

    assert results == []


def test_reranker_rejects_empty_query(
    reranker: RAGReranker,
):
    with pytest.raises(
        ValueError,
        match="Reranking query cannot be empty",
    ):
        reranker.rerank(
            query="   ",
            chunks=[],
        )


def test_reranker_rejects_invalid_limit(
    reranker: RAGReranker,
):
    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        reranker.rerank(
            query="component",
            chunks=[],
            limit=0,
        )


def test_reranker_is_deterministic(
    reranker: RAGReranker,
):
    chunks = [
        make_chunk(
            "chunk-a",
            "voltage regulator",
            0.80,
        ),
        make_chunk(
            "chunk-b",
            "voltage regulator",
            0.80,
        ),
    ]

    first = reranker.rerank(
        query="voltage regulator",
        chunks=chunks,
        limit=2,
    )

    second = reranker.rerank(
        query="voltage regulator",
        chunks=chunks,
        limit=2,
    )

    assert [
        result.chunk.chunk_id
        for result in first
    ] == [
        result.chunk.chunk_id
        for result in second
    ]


def test_reranker_handles_case_insensitively(
    reranker: RAGReranker,
):
    chunks = [
        make_chunk(
            "chunk-1",
            "TEXAS INSTRUMENTS regulator",
            0.80,
        ),
        make_chunk(
            "chunk-2",
            "unrelated component",
            0.90,
        ),
    ]

    results = reranker.rerank(
        query="texas instruments",
        chunks=chunks,
        limit=2,
    )

    assert results[0].chunk.chunk_id == "chunk-1"