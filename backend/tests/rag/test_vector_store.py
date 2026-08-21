import pytest
from qdrant_client import QdrantClient
from unittest.mock import MagicMock

from backend.app.rag.models import DocumentChunk
from backend.app.rag.vector_store import (
    QdrantVectorStore,
)


@pytest.fixture
def client() -> QdrantClient:
    return QdrantClient(":memory:")


@pytest.fixture
def store(
    client: QdrantClient,
) -> QdrantVectorStore:
    vector_store = QdrantVectorStore(
        client,
        collection_name="test_documents",
        vector_size=4,
    )

    vector_store.ensure_collection()

    return vector_store


def make_chunk(
    chunk_id: str,
    text: str,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="DOC-001",
        text=text,
        chunk_index=0,
        metadata={
            "mpn": "TEST-MPN",
            "manufacturer": "Test Manufacturer",
            "source": "test-datasheet.pdf",
            "page_number": 8,
        },
    )


def test_collection_is_created(
    client: QdrantClient,
):
    store = QdrantVectorStore(
        client,
        collection_name="documents",
        vector_size=4,
    )

    store.ensure_collection()

    assert client.collection_exists(
        "documents"
    )


def test_collection_creation_is_idempotent(
    client: QdrantClient,
):
    store = QdrantVectorStore(
        client,
        collection_name="documents",
        vector_size=4,
    )

    store.ensure_collection()
    store.ensure_collection()

    assert client.collection_exists(
        "documents"
    )


def test_upsert_and_search(
    store: QdrantVectorStore,
):
    chunks = [
        make_chunk(
            "DOC-001-chunk-0",
            "Texas Instruments voltage regulator",
        ),
        make_chunk(
            "DOC-001-chunk-1",
            "STMicroelectronics controller",
        ),
    ]

    vectors = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ]

    store.upsert(
        chunks=chunks,
        vectors=vectors,
    )

    results = store.search(
        vector=[1.0, 0.0, 0.0, 0.0],
        limit=2,
    )

    assert len(results) == 2

    assert (
        results[0].chunk.chunk_id
        == "DOC-001-chunk-0"
    )

    assert (
        results[0].chunk.text
        == "Texas Instruments voltage regulator"
    )

    assert results[0].score > 0.9


def test_metadata_is_preserved(
    store: QdrantVectorStore,
):
    chunk = make_chunk(
        "DOC-001-chunk-0",
        "Test component information",
    )

    store.upsert(
        chunks=[chunk],
        vectors=[
            [1.0, 0.0, 0.0, 0.0],
        ],
    )

    results = store.search(
        vector=[1.0, 0.0, 0.0, 0.0],
        limit=1,
    )

    assert len(results) == 1

    result = results[0]

    metadata = result.chunk.metadata

    assert metadata["mpn"] == "TEST-MPN"

    assert metadata["manufacturer"] == (
        "Test Manufacturer"
    )

    assert metadata["source"] == (
        "test-datasheet.pdf"
    )

    assert metadata["page_number"] == 8

    assert (
        result.metadata["collection"]
        == "test_documents"
    )


def test_upsert_rejects_mismatched_counts(
    store: QdrantVectorStore,
):
    chunk = make_chunk(
        "DOC-001-chunk-0",
        "Test",
    )

    with pytest.raises(
        ValueError,
        match=(
            "chunks and vectors must contain "
            "the same number"
        ),
    ):
        store.upsert(
            chunks=[chunk],
            vectors=[],
        )


def test_upsert_rejects_wrong_vector_dimension(
    store: QdrantVectorStore,
):
    chunk = make_chunk(
        "DOC-001-chunk-0",
        "Test",
    )

    with pytest.raises(
        ValueError,
        match="Vector dimension",
    ):
        store.upsert(
            chunks=[chunk],
            vectors=[
                [1.0, 0.0]
            ],
        )


def test_search_rejects_wrong_vector_dimension(
    store: QdrantVectorStore,
):
    with pytest.raises(
        ValueError,
        match="Vector dimension",
    ):
        store.search(
            vector=[1.0, 0.0],
        )


def test_search_rejects_invalid_limit(
    store: QdrantVectorStore,
):
    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        store.search(
            vector=[
                1.0,
                0.0,
                0.0,
                0.0,
            ],
            limit=0,
        )


def test_empty_upsert_is_allowed(
    store: QdrantVectorStore,
):
    store.upsert(
        chunks=[],
        vectors=[],
    )


def test_invalid_collection_name_is_rejected(
    client: QdrantClient,
):
    with pytest.raises(
        ValueError,
        match="collection_name cannot be empty",
    ):
        QdrantVectorStore(
            client,
            collection_name="   ",
            vector_size=4,
        )


def test_invalid_vector_size_is_rejected(
    client: QdrantClient,
):
    with pytest.raises(
        ValueError,
        match="vector_size must be greater than zero",
    ):
        QdrantVectorStore(
            client,
            collection_name="documents",
            vector_size=0,
        )

def test_ensure_collection_rejects_dimension_mismatch():
    client = MagicMock()

    client.collection_exists.return_value = True

    collection = MagicMock()

    collection.config.params.vectors = MagicMock(
        size=8,
    )

    client.get_collection.return_value = collection

    store = QdrantVectorStore(
        client,
        collection_name="bom_documents",
        vector_size=1536,
    )

    with pytest.raises(
        ValueError,
        match="vector dimension mismatch",
    ):
        store.ensure_collection()
