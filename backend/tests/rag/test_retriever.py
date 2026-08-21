import pytest

from backend.app.rag.embeddings import (
    EmbeddingProvider,
)
from backend.app.rag.models import (
    DocumentChunk,
    RetrievedChunk,
)
from backend.app.rag.retriever import (
    RAGRetriever,
)


class FakeEmbeddingProvider(
    EmbeddingProvider
):
    """Deterministic embedding provider for retriever tests."""

    def __init__(
        self,
        vectors: list[list[float]],
    ) -> None:
        self.vectors = vectors
        self.calls: list[list[str]] = []

    @property
    def dimension(self) -> int:
        return 4

    async def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        self.calls.append(texts)
        return self.vectors


class FakeVectorStore:
    """Deterministic vector store for retriever tests."""

    def __init__(
        self,
        results: list[RetrievedChunk],
    ) -> None:
        self.results = results
        self.calls: list[
            tuple[list[float], int]
        ] = []

    def search(
        self,
        *,
        vector: list[float],
        limit: int,
    ) -> list[RetrievedChunk]:
        self.calls.append(
            (vector, limit)
        )

        return self.results[:limit]


def make_chunk(
    chunk_id: str,
    text: str,
    score: float,
) -> RetrievedChunk:
    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id="DOC-001",
        text=text,
        chunk_index=0,
        metadata={
            "mpn": "TEST-MPN",
        },
    )

    return RetrievedChunk(
        chunk=chunk,
        score=score,
        metadata={
            "source": "test",
        },
    )


@pytest.mark.asyncio
async def test_retriever_embeds_query_and_searches(
):
    embedding_provider = FakeEmbeddingProvider(
        vectors=[
            [0.1, 0.2, 0.3, 0.4]
        ]
    )

    expected = [
        make_chunk(
            "DOC-001-chunk-0",
            "Voltage regulator information",
            0.95,
        )
    ]

    vector_store = FakeVectorStore(
        results=expected
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = await retriever.retrieve(
        query="  Voltage regulator  ",
        limit=5,
    )

    assert results == expected

    assert embedding_provider.calls == [
        ["Voltage regulator"]
    ]

    assert vector_store.calls == [
        (
            [0.1, 0.2, 0.3, 0.4],
            5,
        )
    ]


@pytest.mark.asyncio
async def test_retriever_preserves_retrieved_chunk_data(
):
    embedding_provider = FakeEmbeddingProvider(
        vectors=[
            [1.0, 0.0, 0.0, 0.0]
        ]
    )

    expected = [
        make_chunk(
            "DOC-001-chunk-0",
            "Texas Instruments regulator",
            0.91,
        ),
        make_chunk(
            "DOC-001-chunk-1",
            "Regulator operating voltage",
            0.84,
        ),
    ]

    vector_store = FakeVectorStore(
        results=expected
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = await retriever.retrieve(
        query="regulator",
        limit=2,
    )

    assert len(results) == 2

    assert (
        results[0].chunk.chunk_id
        == "DOC-001-chunk-0"
    )

    assert (
        results[0].chunk.text
        == "Texas Instruments regulator"
    )

    assert results[0].score == 0.91

    assert (
        results[0].metadata["source"]
        == "test"
    )


@pytest.mark.asyncio
async def test_retriever_passes_limit_to_vector_store(
):
    embedding_provider = FakeEmbeddingProvider(
        vectors=[
            [1.0, 0.0, 0.0, 0.0]
        ]
    )

    expected = [
        make_chunk(
            "DOC-001-chunk-0",
            "First result",
            0.95,
        ),
        make_chunk(
            "DOC-001-chunk-1",
            "Second result",
            0.85,
        ),
        make_chunk(
            "DOC-001-chunk-2",
            "Third result",
            0.75,
        ),
    ]

    vector_store = FakeVectorStore(
        results=expected
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = await retriever.retrieve(
        query="test query",
        limit=2,
    )

    assert len(results) == 2

    assert vector_store.calls == [
        (
            [1.0, 0.0, 0.0, 0.0],
            2,
        )
    ]


@pytest.mark.asyncio
async def test_retriever_rejects_empty_query(
):
    embedding_provider = FakeEmbeddingProvider(
        vectors=[
            [1.0, 0.0, 0.0, 0.0]
        ]
    )

    vector_store = FakeVectorStore(
        results=[]
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(
        ValueError,
        match="Retrieval query cannot be empty",
    ):
        await retriever.retrieve(
            query="   ",
        )

    assert embedding_provider.calls == []
    assert vector_store.calls == []


@pytest.mark.asyncio
async def test_retriever_rejects_invalid_limit(
):
    embedding_provider = FakeEmbeddingProvider(
        vectors=[
            [1.0, 0.0, 0.0, 0.0]
        ]
    )

    vector_store = FakeVectorStore(
        results=[]
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        await retriever.retrieve(
            query="test",
            limit=0,
        )

    assert embedding_provider.calls == []
    assert vector_store.calls == []


@pytest.mark.asyncio
async def test_retriever_rejects_multiple_embedding_vectors(
):
    embedding_provider = FakeEmbeddingProvider(
        vectors=[
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ]
    )

    vector_store = FakeVectorStore(
        results=[]
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Embedding provider must return exactly "
            "one vector"
        ),
    ):
        await retriever.retrieve(
            query="test",
        )

    assert embedding_provider.calls == [
        ["test"]
    ]

    assert vector_store.calls == []


@pytest.mark.asyncio
async def test_retriever_returns_empty_when_no_chunks_match(
):
    embedding_provider = FakeEmbeddingProvider(
        vectors=[
            [1.0, 0.0, 0.0, 0.0]
        ]
    )

    vector_store = FakeVectorStore(
        results=[]
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    results = await retriever.retrieve(
        query="component datasheet",
    )

    assert results == []

    assert vector_store.calls == [
        (
            [1.0, 0.0, 0.0, 0.0],
            5,
        )
    ]
