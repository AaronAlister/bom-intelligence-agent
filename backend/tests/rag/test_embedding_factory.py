import pytest

from backend.app.rag.embedding_factory import (
    build_embedding_provider,
)
from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
    OpenAIEmbeddingProvider,
)


def test_factory_builds_deterministic_provider():
    provider = build_embedding_provider(
        provider="deterministic",
        dimension=8,
        model="unused",
        api_key="",
    )

    assert isinstance(
        provider,
        DeterministicEmbeddingProvider,
    )

    assert provider.dimension == 8


def test_factory_is_case_insensitive():
    provider = build_embedding_provider(
        provider="DETERMINISTIC",
        dimension=8,
        model="unused",
        api_key="",
    )

    assert isinstance(
        provider,
        DeterministicEmbeddingProvider,
    )


def test_factory_builds_openai_provider():
    provider = build_embedding_provider(
        provider="openai",
        dimension=1536,
        model="text-embedding-3-small",
        api_key="test-key",
    )

    assert isinstance(
        provider,
        OpenAIEmbeddingProvider,
    )

    assert provider.dimension == 1536


def test_factory_rejects_unknown_provider():
    with pytest.raises(
        ValueError,
        match="Unsupported embedding provider",
    ):
        build_embedding_provider(
            provider="unknown",
            dimension=8,
            model="unused",
            api_key="",
        )