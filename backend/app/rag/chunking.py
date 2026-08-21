from typing import Any

from backend.app.rag.documents.models import ParsedDocument
from backend.app.rag.models import (
    Document,
    DocumentChunk,
)


class DocumentChunker:
    """
    Deterministic document chunker.

    Supports both:
    - standard document text chunking
    - page-aware chunking with provenance metadata
    """

    def __init__(
        self,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than zero."
            )

        if chunk_overlap < 0:
            raise ValueError(
                "chunk_overlap cannot be negative."
            )

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        document: Document,
        text: str,
    ) -> list[DocumentChunk]:
        """
        Split document text into deterministic overlapping chunks.

        Empty or whitespace-only documents produce no chunks.
        """

        normalized_text = text.strip()

        if not normalized_text:
            return []

        return self._chunk_text(
            document=document,
            text=normalized_text,
        )

    def chunk_parsed_document(
        self,
        parsed_document: ParsedDocument,
    ) -> list[DocumentChunk]:
        """
        Chunk a page-aware ParsedDocument.

        Each page is processed independently so chunks never
        silently lose their page provenance.
        """

        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for page in parsed_document.pages:
            normalized_text = page.text.strip()

            if not normalized_text:
                continue

            page_chunks = self._chunk_text(
                document=parsed_document.document,
                text=normalized_text,
                chunk_index_start=chunk_index,
                extra_metadata={
                    **page.metadata,
                    "page_number": page.page_number,
                },
            )

            chunks.extend(page_chunks)
            chunk_index += len(page_chunks)

        return chunks

    def chunk_pages(
        self,
        document: Document,
        pages: list[dict[str, Any]],
    ) -> list[DocumentChunk]:
        """
        Split page dictionaries into page-aware chunks.

        This method remains available for callers that already
        provide page dictionaries.
        """

        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for page in pages:
            page_number = page.get("page_number")
            page_text = page.get("text")

            if not isinstance(page_number, int):
                raise ValueError(
                    "Each page must contain an integer page_number."
                )

            if not isinstance(page_text, str):
                raise ValueError(
                    "Each page must contain string text."
                )

            normalized_text = page_text.strip()

            if not normalized_text:
                continue

            page_chunks = self._chunk_text(
                document=document,
                text=normalized_text,
                chunk_index_start=chunk_index,
                extra_metadata={
                    **page,
                    "page_number": page_number,
                },
            )

            chunks.extend(page_chunks)
            chunk_index += len(page_chunks)

        return chunks

    def _chunk_text(
        self,
        *,
        document: Document,
        text: str,
        chunk_index_start: int = 0,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """
        Internal deterministic text chunking implementation.
        """

        chunks: list[DocumentChunk] = []

        step = (
            self.chunk_size
            - self.chunk_overlap
        )

        start = 0
        chunk_index = chunk_index_start

        while start < len(text):
            end = min(
                start + self.chunk_size,
                len(text),
            )

            chunk_text = text[start:end].strip()

            if chunk_text:
                metadata: dict[str, Any] = {
                    **document.metadata,
                    "title": document.title,
                    "source": document.source,
                    "source_url": document.source_url,
                    "manufacturer": document.manufacturer,
                    "mpn": document.mpn,
                }

                if extra_metadata is not None:
                    metadata.update(extra_metadata)

                chunks.append(
                    DocumentChunk(
                        chunk_id=(
                            f"{document.document_id}"
                            f"-chunk-{chunk_index}"
                        ),
                        document_id=document.document_id,
                        text=chunk_text,
                        chunk_index=chunk_index,
                        metadata=metadata,
                    )
                )

                chunk_index += 1

            if end >= len(text):
                break

            start += step

        return chunks