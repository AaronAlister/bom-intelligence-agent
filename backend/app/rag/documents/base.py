from abc import ABC, abstractmethod
from pathlib import Path

from backend.app.rag.documents.models import ParsedDocument


class DocumentLoader(ABC):
    """
    Interface for engineering document loaders.

    A loader reads a source document and produces a
    page-aware ParsedDocument.

    Loaders do not perform:
    - RAG chunking
    - embedding
    - vector indexing
    - retrieval
    - reranking
    - evidence generation
    """

    supported_extensions: set[str] = set()

    @abstractmethod
    def load(
        self,
        file_path: Path,
    ) -> ParsedDocument:
        """
        Load and parse a document.
        """
        raise NotImplementedError

    def supports(
        self,
        extension: str,
    ) -> bool:
        """
        Return whether this loader supports the extension.
        """
        return extension.lower() in self.supported_extensions