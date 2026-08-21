from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
    OpenAIEmbeddingProvider,
)


@pytest.mark.asyncio
async def test_embedding_provider_returns_one_vector_per_text():
    provider = DeterministicEmbeddingProvider(
        dimension=8,
    )

    vectors = await provider.embed(
        [
            "first component",
            "second component",
            "third component",
        ]
    )

    assert len(vectors) == 3

    assert all(
        len(vector) == 8
        for vector in vectors
    )


@pytest.mark.asyncio
async def test_embedding_provider_is_deterministic():
    provider = DeterministicEmbeddingProvider(
        dimension=8,
    )

    first = await provider.embed(
        ["TPS7A4901 datasheet"]
    )

    second = await provider.embed(
        ["TPS7A4901 datasheet"]
    )

    assert first == second


@pytest.mark.asyncio
async def test_different_texts_produce_different_vectors():
    provider = DeterministicEmbeddingProvider(
        dimension=8,
    )

    vectors = await provider.embed(
        [
            "Texas Instruments regulator",
            "STMicroelectronics controller",
        ]
    )

    assert vectors[0] != vectors[1]


@pytest.mark.asyncio
async def test_empty_input_returns_empty_result():
    provider = DeterministicEmbeddingProvider()

    vectors = await provider.embed([])

    assert vectors == []


def test_embedding_dimension_is_exposed():
    provider = DeterministicEmbeddingProvider(
        dimension=16,
    )

    assert provider.dimension == 16


def test_invalid_dimension_is_rejected():
    with pytest.raises(
        ValueError,
        match="dimension must be greater than zero",
    ):
        DeterministicEmbeddingProvider(
            dimension=0,
        )


@pytest.mark.asyncio
async def test_vector_values_are_normalized():
    provider = DeterministicEmbeddingProvider(
        dimension=8,
    )

    vectors = await provider.embed(
        ["test text"]
    )

    vector = vectors[0]

    assert all(
        0.0 <= value <= 1.0
        for value in vector
    )


def build_openai_response(
    vectors: list[list[float]],
) -> MagicMock:
    response = MagicMock()

    response.data = [
        MagicMock(
            embedding=vector,
        )
        for vector in vectors
    ]

    return response


def test_openai_embedding_provider_dimension_is_exposed():
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        dimension=3,
    )

    assert provider.dimension == 3


def test_openai_embedding_provider_rejects_empty_api_key():
    with pytest.raises(
        ValueError,
        match="OpenAI API key cannot be empty",
    ):
        OpenAIEmbeddingProvider(
            api_key="   ",
        )


def test_openai_embedding_provider_rejects_empty_model():
    with pytest.raises(
        ValueError,
        match="Embedding model cannot be empty",
    ):
        OpenAIEmbeddingProvider(
            api_key="test-key",
            model="   ",
        )


@pytest.mark.asyncio
async def test_openai_embedding_provider_embeds_texts(
    monkeypatch,
):
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimension=3,
    )

    mock_create = AsyncMock(
        return_value=build_openai_response(
            [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
            ]
        )
    )

    monkeypatch.setattr(
        provider._client.embeddings,
        "create",
        mock_create,
    )

    vectors = await provider.embed(
        [
            " first ",
            "second",
        ]
    )

    assert vectors == [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]

    mock_create.assert_awaited_once_with(
        model="text-embedding-3-small",
        input=[
            "first",
            "second",
        ],
        dimensions=3,
    )


@pytest.mark.asyncio
async def test_openai_embedding_provider_returns_empty_result_for_empty_input(
    monkeypatch,
):
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        dimension=3,
    )

    mock_create = AsyncMock()

    monkeypatch.setattr(
        provider._client.embeddings,
        "create",
        mock_create,
    )

    vectors = await provider.embed([])

    assert vectors == []

    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_openai_embedding_provider_rejects_empty_texts(
    monkeypatch,
):
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        dimension=3,
    )

    mock_create = AsyncMock()

    monkeypatch.setattr(
        provider._client.embeddings,
        "create",
        mock_create,
    )

    with pytest.raises(
        ValueError,
        match="Embedding input texts cannot be empty",
    ):
        await provider.embed(
            [
                "valid",
                "   ",
            ]
        )

    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_openai_embedding_provider_rejects_wrong_vector_count(
    monkeypatch,
):
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        dimension=3,
    )

    mock_create = AsyncMock(
        return_value=build_openai_response(
            [
                [0.1, 0.2, 0.3],
            ]
        )
    )

    monkeypatch.setattr(
        provider._client.embeddings,
        "create",
        mock_create,
    )

    with pytest.raises(
        ValueError,
        match="unexpected number of vectors",
    ):
        await provider.embed(
            [
                "first",
                "second",
            ]
        )


@pytest.mark.asyncio
async def test_openai_embedding_provider_rejects_wrong_vector_dimension(
    monkeypatch,
):
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        dimension=3,
    )

    mock_create = AsyncMock(
        return_value=build_openai_response(
            [
                [0.1, 0.2],
            ]
        )
    )

    monkeypatch.setattr(
        provider._client.embeddings,
        "create",
        mock_create,
    )

    with pytest.raises(
        ValueError,
        match="unexpected dimension",
    ):
        await provider.embed(
            ["test text"]
        )
