from abc import ABC, abstractmethod
from hashlib import sha256

from openai import AsyncOpenAI


class EmbeddingProvider(ABC):
    """
    Provider-agnostic interface for text embeddings.

    The RAG pipeline depends on this interface rather than
    a specific embedding model or vendor.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of generated vectors."""
        raise NotImplementedError

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Convert texts into embedding vectors.

        Implementations must return exactly one vector
        for every input text.
        """
        raise NotImplementedError


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """
    Small deterministic embedding provider for tests.

    This is NOT a production semantic embedding model.
    It exists to validate the RAG architecture without
    requiring an external model or API.
    """

    def __init__(
        self,
        *,
        dimension: int = 8,
    ) -> None:
        if dimension <= 0:
            raise ValueError(
                "dimension must be greater than zero."
            )

        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        return [
            self._embed_text(text)
            for text in texts
        ]

    def _embed_text(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate a deterministic vector from text.

        SHA-256 is used only to provide stable test vectors.
        It has no semantic meaning and must not be used as
        the production retrieval embedding.
        """

        digest = sha256(
            text.encode("utf-8")
        ).digest()

        values: list[float] = []

        for index in range(self.dimension):
            byte = digest[
                index % len(digest)
            ]

            values.append(
                byte / 255.0
            )

        return values


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Production embedding provider backed by OpenAI.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "OpenAI API key cannot be empty."
            )

        if not model.strip():
            raise ValueError(
                "Embedding model cannot be empty."
            )

        if dimension <= 0:
            raise ValueError(
                "dimension must be greater than zero."
            )

        self._client = AsyncOpenAI(
            api_key=api_key,
        )

        self._model = model
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        normalized_texts = [
            text.strip()
            for text in texts
        ]

        if any(
            not text
            for text in normalized_texts
        ):
            raise ValueError(
                "Embedding input texts cannot be empty."
            )

        response = await self._client.embeddings.create(
            model=self._model,
            input=normalized_texts,
            dimensions=self._dimension,
        )

        vectors = [
            item.embedding
            for item in response.data
        ]

        if len(vectors) != len(texts):
            raise ValueError(
                "Embedding provider returned an unexpected "
                "number of vectors."
            )

        for vector in vectors:
            if len(vector) != self._dimension:
                raise ValueError(
                    "Embedding provider returned a vector "
                    "with an unexpected dimension."
                )

        return vectors
