import pytest

from backend.app.rag.evidence import (
    RAGEvidenceBuilder,
)
from backend.app.rag.models import (
    DocumentChunk,
    RetrievedChunk,
)
from backend.app.rag.reranker import (
    RAGReranker,
)
from backend.app.rag.service import (
    RAGService,
)


class FakeRetriever:
    """Deterministic retriever for service tests."""

    def __init__(
        self,
        results: list[RetrievedChunk],
    ) -> None:
        self.results = results
        self.calls: list[
            tuple[str, int]
        ] = []

    async def retrieve(
        self,
        *,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        self.calls.append(
            (query, limit)
        )

        return self.results[:limit]


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
        ),
        score=score,
    )


@pytest.fixture
def chunks() -> list[RetrievedChunk]:
    return [
        make_chunk(
            "chunk-1",
            "LM358 operational amplifier",
            0.95,
        ),
        make_chunk(
            "chunk-2",
            "Generic resistor information",
            0.70,
        ),
    ]


@pytest.fixture
def service(
    chunks: list[RetrievedChunk],
) -> tuple[RAGService, FakeRetriever]:
    retriever = FakeRetriever(chunks)

    service = RAGService(
        retriever=retriever,
        reranker=RAGReranker(),
        evidence_builder=RAGEvidenceBuilder(),
    )

    return service, retriever


@pytest.mark.asyncio
async def test_rag_service_runs_complete_pipeline(
    service: tuple[
        RAGService,
        FakeRetriever,
    ],
):
    rag_service, retriever = service

    evidence = await rag_service.retrieve_evidence(
        query="LM358 operational amplifier",
    )

    assert len(evidence) == 2

    assert (
        evidence[0].metadata["chunk_id"]
        == "chunk-1"
    )

    assert (
        evidence[0].source
        == "rag"
    )

    assert retriever.calls == [
        (
            "LM358 operational amplifier",
            10,
        )
    ]


@pytest.mark.asyncio
async def test_rag_service_respects_evidence_limit(
    service: tuple[
        RAGService,
        FakeRetriever,
    ],
):
    rag_service, _ = service

    evidence = await rag_service.retrieve_evidence(
        query="LM358",
        retrieval_limit=10,
        evidence_limit=1,
    )

    assert len(evidence) == 1


@pytest.mark.asyncio
async def test_rag_service_respects_retrieval_limit(
    service: tuple[
        RAGService,
        FakeRetriever,
    ],
):
    rag_service, retriever = service

    await rag_service.retrieve_evidence(
        query="LM358",
        retrieval_limit=1,
        evidence_limit=1,
    )

    assert retriever.calls == [
        (
            "LM358",
            1,
        )
    ]


@pytest.mark.asyncio
async def test_rag_service_returns_empty_when_retriever_returns_empty():
    retriever = FakeRetriever([])

    service = RAGService(
        retriever=retriever,
        reranker=RAGReranker(),
        evidence_builder=RAGEvidenceBuilder(),
    )

    evidence = await service.retrieve_evidence(
        query="component",
    )

    assert evidence == []


@pytest.mark.asyncio
async def test_rag_service_propagates_empty_query_error(
    service: tuple[
        RAGService,
        FakeRetriever,
    ],
):
    rag_service, _ = service

    with pytest.raises(
        ValueError,
        match="Retrieval query cannot be empty",
    ):
        await rag_service.retrieve_evidence(
            query="   ",
        )


@pytest.mark.asyncio
async def test_rag_service_rejects_invalid_retrieval_limit(
    service: tuple[
        RAGService,
        FakeRetriever,
    ],
):
    rag_service, _ = service

    with pytest.raises(
        ValueError,
        match="retrieval_limit must be greater than zero",
    ):
        await rag_service.retrieve_evidence(
            query="component",
            retrieval_limit=0,
        )


@pytest.mark.asyncio
async def test_rag_service_rejects_invalid_evidence_limit(
    service: tuple[
        RAGService,
        FakeRetriever,
    ],
):
    rag_service, _ = service

    with pytest.raises(
        ValueError,
        match="evidence_limit must be greater than zero",
    ):
        await rag_service.retrieve_evidence(
            query="component",
            evidence_limit=0,
        )