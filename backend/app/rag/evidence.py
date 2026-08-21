from backend.app.agents.contracts import Evidence
from backend.app.rag.models import RetrievedChunk


class RAGEvidenceBuilder:
    """
    Converts retrieved RAG chunks into the agent's
    standardized Evidence contract.

    This layer does not generate new claims. It only
    packages retrieved source material into traceable
    evidence objects.
    """

    SOURCE = "rag"

    def build(
        self,
        chunks: list[RetrievedChunk],
        *,
        limit: int | None = None,
    ) -> list[Evidence]:
        """
        Convert retrieved chunks into agent evidence.

        Evidence preserves source identity, chunk identity,
        retrieval scores, and original metadata.
        """

        if limit is not None and limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        selected_chunks = (
            chunks
            if limit is None
            else chunks[:limit]
        )

        return [
            self._build_evidence(chunk)
            for chunk in selected_chunks
        ]

    @classmethod
    def _build_evidence(
        cls,
        retrieved: RetrievedChunk,
    ) -> Evidence:
        chunk = retrieved.chunk

        metadata = {
            "document_id": chunk.document_id,
            "chunk_id": chunk.chunk_id,
            "chunk_index": chunk.chunk_index,
            "score": retrieved.score,
            "chunk_metadata": chunk.metadata,
            "retrieval_metadata": retrieved.metadata,
        }

        return Evidence(
            source=cls.SOURCE,
            source_id=chunk.document_id,
            excerpt=chunk.text,
            metadata=metadata,
        )