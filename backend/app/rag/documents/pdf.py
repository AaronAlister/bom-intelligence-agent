import hashlib
from pathlib import Path

import fitz

from backend.app.rag.documents.base import DocumentLoader
from backend.app.rag.documents.cleaning import clean_extracted_text
from backend.app.rag.documents.models import (
    ParsedDocument,
    ParsedPage,
)
from backend.app.rag.models import Document


class PDFDocumentLoader(DocumentLoader):
    """
    PDF document loader backed by PyMuPDF.

    The loader extracts text page by page and preserves
    page boundaries for downstream provenance.
    """

    supported_extensions: set[str] = {".pdf"}

    def load(
        self,
        file_path: Path,
    ) -> ParsedDocument:
        """
        Load a PDF and return a page-aware ParsedDocument.

        Raises:
            FileNotFoundError:
                If the supplied file does not exist.

            ValueError:
                If the file is not a PDF or contains no
                extractable text.

            RuntimeError:
                If the PDF cannot be opened or processed.
        """

        if not file_path.exists():
            raise FileNotFoundError(
                f"PDF file does not exist: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"PDF path is not a file: {file_path}"
            )

        if not self.supports(file_path.suffix):
            raise ValueError(
                f"Unsupported document extension: "
                f"{file_path.suffix}"
            )

        try:
            document_bytes = file_path.read_bytes()
        except OSError as exc:
            raise RuntimeError(
                f"Unable to read PDF file: {file_path}"
            ) from exc

        document_id = self._build_document_id(
            document_bytes
        )

        document = Document(
            document_id=document_id,
            title=file_path.stem,
            source=file_path.name,
            metadata={
                "document_type": "pdf",
            },
        )

        try:
            pdf_document = fitz.open(
                stream=document_bytes,
                filetype="pdf",
            )
        except (RuntimeError, ValueError) as exc:
            raise RuntimeError(
                f"Unable to open PDF file: {file_path}"
            ) from exc

        pages: list[ParsedPage] = []

        try:
            for page_index in range(
                pdf_document.page_count
            ):
                page = pdf_document.load_page(
                    page_index
                )

                extracted_text = page.get_text(
                    "text"
                )

                if not isinstance(
                    extracted_text,
                    str,
                ):
                    raise RuntimeError(
                        "PDF text extraction returned "
                        "a non-text result."
                    )

                page_text = clean_extracted_text(
                    extracted_text
                )

                pages.append(
                    ParsedPage(
                        page_number=page_index + 1,
                        text=page_text,
                        metadata={
                            "page_number": page_index + 1,
                        },
                    )
                )
        except (RuntimeError, ValueError) as exc:
            raise RuntimeError(
                f"Unable to extract text from PDF: "
                f"{file_path}"
            ) from exc
        finally:
            pdf_document.close()

        if not pages:
            raise ValueError(
                f"PDF contains no pages: {file_path}"
            )

        has_extractable_text = any(
            page.text.strip()
            for page in pages
        )

        if not has_extractable_text:
            raise ValueError(
                f"PDF contains no extractable text: "
                f"{file_path}"
            )

        document.metadata["page_count"] = len(
            pages
        )

        return ParsedDocument(
            document=document,
            pages=pages,
        )

    @staticmethod
    def _build_document_id(
        document_bytes: bytes,
    ) -> str:
        """
        Build a deterministic document ID from file content.

        Identical PDF content receives the same
        document identity.
        """

        digest = hashlib.sha256(
            document_bytes
        ).hexdigest()

        return f"DOC-{digest}"
