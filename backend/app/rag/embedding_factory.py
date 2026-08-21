from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
)


def build_embedding_provider(
    *,
    provider: str,
    dimension: int,
    model: str,
    api_key: str,
) -> EmbeddingProvider:
    """
    Construct the configured embedding provider.

    Supported providers:
    - deterministic
    - openai
    """

    normalized_provider = provider.strip().lower()

    if normalized_provider == "deterministic":
        return DeterministicEmbeddingProvider(
            dimension=dimension,
        )

    if normalized_provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model=model,
            dimension=dimension,
        )

    raise ValueError(
        f"Unsupported embedding provider: {provider}"
    )