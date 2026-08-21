from pathlib import Path
from typing import Protocol, TypedDict

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.documents.models import ParsedDocument
from backend.app.rag.models import DocumentChunk


class DocumentLoaderProtocol(Protocol):
    """
    Interface required by the document ingestion service.
    """

    def load(
        self,
        file_path: Path,
    ) -> ParsedDocument:
        ...


class DocumentIndexerProtocol(Protocol):
    """
    Interface required by the document ingestion service.
    """

    async def index(
        self,
        *,
        chunks: list[DocumentChunk],
    ) -> int:
        ...


class DocumentIngestionPersistenceProtocol(Protocol):
    """
    Interface required for persisting ingestion results.
    """

    async def record_success(
        self,
        *,
        document_id: str,
        source_file: str,
        source_format: str,
        pages_processed: int,
        chunks_created: int,
        chunks_indexed: int,
    ) -> None:
        ...


class DocumentIngestionResult(TypedDict):
    """
    Statistics returned after engineering document ingestion.
    """

    document_id: str
    source: str
    pages_processed: int
    chunks_created: int
    chunks_indexed: int


class DocumentIngestionService:
    """
    Orchestrates engineering document ingestion.

    The service:
    1. Loads a source document.
    2. Preserves page-aware structure.
    3. Creates page-aware RAG chunks.
    4. Delegates vector indexing.
    5. Returns ingestion statistics.
    """

    def __init__(
        self,
        *,
        loader: DocumentLoaderProtocol,
        chunker: DocumentChunker,
        indexer: DocumentIndexerProtocol,
        persistence: DocumentIngestionPersistenceProtocol | None = None,
    ) -> None:
        self._loader = loader
        self._chunker = chunker
        self._indexer = indexer
        self._persistence = persistence

    async def ingest(
        self,
        *,
        file_path: Path,
    ) -> DocumentIngestionResult:
        """
        Load, chunk, and index an engineering document.
        """

        parsed_document = self._loader.load(
            file_path
        )

        chunks = self._chunker.chunk_parsed_document(
            parsed_document
        )

        if not chunks:
            raise ValueError(
                "No searchable content found in document."
            )

        indexed_count = await self._indexer.index(
            chunks=chunks,
        )

        if self._persistence is not None:
            await self._persistence.record_success(
                document_id=parsed_document.document.document_id,
                source_file=parsed_document.document.source,
                source_format="pdf",
                pages_processed=len(parsed_document.pages),
                chunks_created=len(chunks),
                chunks_indexed=indexed_count,
            )

        return {
            "document_id": (
                parsed_document.document.document_id
            ),
            "source": (
                parsed_document.document.source
            ),
            "pages_processed": len(
                parsed_document.pages
            ),
            "chunks_created": len(chunks),
            "chunks_indexed": indexed_count,
        }