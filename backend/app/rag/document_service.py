from typing import TypedDict

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.indexer import VectorIndexer
from backend.app.rag.models import Document


class DocumentIndexResult(TypedDict):
    """
    Statistics returned after indexing a document.
    """

    document_id: str
    chunks_created: int
    chunks_indexed: int


class RAGDocumentService:
    """
    Orchestrates document chunking and vector indexing.

    The service accepts a source Document and its raw text,
    converts the text into retrieval chunks, and delegates
    vector indexing to the RAG indexer.
    """

    def __init__(
        self,
        *,
        chunker: DocumentChunker,
        indexer: VectorIndexer,
    ) -> None:
        self._chunker = chunker
        self._indexer = indexer

    async def index_document(
        self,
        *,
        document: Document,
        text: str,
    ) -> DocumentIndexResult:
        """
        Chunk and index a document.

        Returns indexing statistics containing the document ID,
        number of chunks created, and number of chunks indexed.
        """

        chunks = self._chunker.chunk(
            document,
            text,
        )

        indexed_count = await self._indexer.index(
            chunks=chunks,
        )

        return {
            "document_id": document.document_id,
            "chunks_created": len(chunks),
            "chunks_indexed": indexed_count,
        }
