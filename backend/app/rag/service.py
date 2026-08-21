from typing import Protocol

from backend.app.agents.contracts import Evidence
from backend.app.rag.evidence import RAGEvidenceBuilder
from backend.app.rag.models import RetrievedChunk
from backend.app.rag.reranker import RAGReranker


class Retriever(Protocol):
    """
    Interface required by the RAG orchestration layer.

    The service only needs a retriever capable of returning
    RetrievedChunk objects for a query.
    """

    async def retrieve(
        self,
        *,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        ...


class RAGService:
    """
    Coordinates retrieval, reranking, and evidence generation.

    The service contains no domain-specific BOM intelligence.
    It only orchestrates the RAG pipeline.
    """

    def __init__(
        self,
        *,
        retriever: Retriever,
        reranker: RAGReranker,
        evidence_builder: RAGEvidenceBuilder,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._evidence_builder = evidence_builder

    async def retrieve_evidence(
        self,
        *,
        query: str,
        retrieval_limit: int = 10,
        evidence_limit: int = 5,
    ) -> list[Evidence]:
        """
        Run the complete RAG pipeline and return
        standardized agent evidence.
        """

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "Retrieval query cannot be empty."
            )

        if retrieval_limit <= 0:
            raise ValueError(
                "retrieval_limit must be greater than zero."
            )

        if evidence_limit <= 0:
            raise ValueError(
                "evidence_limit must be greater than zero."
            )

        chunks = await self._retriever.retrieve(
            query=normalized_query,
            limit=retrieval_limit,
        )

        reranked_chunks = self._reranker.rerank(
            query=normalized_query,
            chunks=chunks,
            limit=retrieval_limit,
        )

        return self._evidence_builder.build(
            reranked_chunks,
            limit=evidence_limit,
        )
