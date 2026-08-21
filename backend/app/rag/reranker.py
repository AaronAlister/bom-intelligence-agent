import re

from backend.app.rag.models import RetrievedChunk


class RAGReranker:
    """
    Deterministic reranker for retrieved document chunks.

    The reranker combines the original retrieval score with
    query-term overlap. It does not perform embedding generation
    or vector search.
    """

    def rerank(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Rerank retrieved chunks and return the highest-ranked results.
        """

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "Reranking query cannot be empty."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        if not chunks:
            return []

        query_terms = self._tokenize(
            normalized_query
        )

        scored_chunks = [
            (
                self._rerank_score(
                    query_terms,
                    retrieved,
                ),
                index,
                retrieved,
            )
            for index, retrieved in enumerate(chunks)
        ]

        scored_chunks.sort(
            key=lambda item: (
                -item[0],
                item[1],
            )
        )

        return [
            retrieved
            for _, _, retrieved in scored_chunks[:limit]
        ]

    @classmethod
    def _rerank_score(
        cls,
        query_terms: set[str],
        retrieved: RetrievedChunk,
    ) -> float:
        """
        Combine vector similarity with lexical query overlap.

        Retrieval score contributes 70%.
        Query-term coverage contributes 30%.
        """

        retrieval_score = max(
            0.0,
            min(
                1.0,
                retrieved.score,
            ),
        )

        if not query_terms:
            return retrieval_score

        text_terms = cls._tokenize(
            retrieved.chunk.text
        )

        overlap = query_terms.intersection(
            text_terms
        )

        coverage = (
            len(overlap) / len(query_terms)
        )

        return (
            retrieval_score * 0.7
            + coverage * 0.3
        )

    @staticmethod
    def _tokenize(
        text: str,
    ) -> set[str]:
        """
        Normalize text into simple alphanumeric terms.
        """

        return {
            token.lower()
            for token in re.findall(
                r"\b[a-zA-Z0-9]+\b",
                text,
            )
        }