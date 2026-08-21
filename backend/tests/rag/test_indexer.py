import pytest

from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.indexer import RAGIndexer
from backend.app.rag.models import DocumentChunk
from backend.app.rag.vector_store import QdrantVectorStore


class FakeEmbeddingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 3

    async def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            [0.1, 0.2, 0.3]
            for _ in texts
        ]


class FakeVectorStore(QdrantVectorStore):
    def __init__(self) -> None:
        self.chunks = None
        self.vectors = None

    def upsert(
        self,
        *,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        self.chunks = chunks
        self.vectors = vectors


def make_chunk(
    chunk_id: str,
    text: str,
    index: int,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="DOC-001",
        text=text,
        chunk_index=index,
    )


@pytest.mark.asyncio
async def test_index_embeds_and_stores_chunks():
    provider = FakeEmbeddingProvider()
    store = FakeVectorStore()

    indexer = RAGIndexer(
        embedding_provider=provider,
        vector_store=store,
    )

    chunks = [
        make_chunk(
            "CHUNK-001",
            "Voltage rating is 5V.",
            0,
        ),
        make_chunk(
            "CHUNK-002",
            "Operating temperature is 85C.",
            1,
        ),
    ]

    result = await indexer.index(
        chunks=chunks,
    )

    assert result == 2
    assert store.chunks == chunks
    assert store.vectors == [
        [0.1, 0.2, 0.3],
        [0.1, 0.2, 0.3],
    ]


@pytest.mark.asyncio
async def test_index_empty_chunks_returns_zero():
    provider = FakeEmbeddingProvider()
    store = FakeVectorStore()

    indexer = RAGIndexer(
        embedding_provider=provider,
        vector_store=store,
    )

    result = await indexer.index(
        chunks=[],
    )

    assert result == 0
    assert store.chunks is None
    assert store.vectors is None


class BrokenEmbeddingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 3

    async def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return []


@pytest.mark.asyncio
async def test_index_rejects_wrong_embedding_count():
    provider = BrokenEmbeddingProvider()
    store = FakeVectorStore()

    indexer = RAGIndexer(
        embedding_provider=provider,
        vector_store=store,
    )

    chunks = [
        make_chunk(
            "CHUNK-001",
            "Test content.",
            0,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="exactly one vector for every document chunk",
    ):
        await indexer.index(
            chunks=chunks,
        )