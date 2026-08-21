from unittest.mock import MagicMock

from backend.app.rag.initialization import (
    initialize_rag_vector_store,
)


def test_initialize_rag_vector_store_creates_store(
    monkeypatch,
):
    fake_store = MagicMock()

    monkeypatch.setattr(
        "backend.app.rag.initialization.QdrantVectorStore",
        lambda *args, **kwargs: fake_store,
    )

    store = initialize_rag_vector_store()

    assert store is fake_store

    fake_store.ensure_collection.assert_called_once()