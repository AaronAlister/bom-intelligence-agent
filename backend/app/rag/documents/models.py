from pydantic import BaseModel, Field

from backend.app.rag.models import Document


class ParsedPage(BaseModel):
    """
    A single extracted document page.

    Page numbers are preserved for downstream provenance.
    """

    page_number: int = Field(
        ...,
        ge=1,
    )

    text: str

    metadata: dict[str, object] = Field(
        default_factory=dict,
    )


class ParsedDocument(BaseModel):
    """
    Page-aware result produced by a document loader.

    The existing RAG Document remains responsible for
    document identity and document-level metadata.
    """

    document: Document

    pages: list[ParsedPage] = Field(
        default_factory=list,
    )

    @property
    def text(self) -> str:
        """
        Return extracted text in page order.

        Empty pages are excluded.
        """
        return "\n\n".join(
            page.text
            for page in self.pages
            if page.text.strip()
        )