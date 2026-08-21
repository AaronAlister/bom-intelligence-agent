from pathlib import Path

import pytest

from backend.app.rag.documents.base import DocumentLoader
from backend.app.rag.documents.models import (
    ParsedDocument,
    ParsedPage,
)
from backend.app.rag.models import Document


def make_document() -> Document:
    return Document(
        document_id="DOC-001",
        title="Sample Datasheet",
        source="Texas Instruments",
        manufacturer="Texas Instruments",
        mpn="TPS7A4901",
    )


def test_parsed_page_accepts_valid_page_number() -> None:
    page = ParsedPage(
        page_number=1,
        text="Input voltage: 3 V to 36 V",
    )

    assert page.page_number == 1
    assert page.text == "Input voltage: 3 V to 36 V"


def test_parsed_page_rejects_zero_page_number() -> None:
    with pytest.raises(ValueError):
        ParsedPage(
            page_number=0,
            text="Invalid page",
        )


def test_parsed_page_rejects_negative_page_number() -> None:
    with pytest.raises(ValueError):
        ParsedPage(
            page_number=-1,
            text="Invalid page",
        )


def test_parsed_page_metadata_defaults_to_empty_dictionary() -> None:
    page = ParsedPage(
        page_number=1,
        text="Electrical characteristics",
    )

    assert page.metadata == {}


def test_parsed_document_preserves_document_identity() -> None:
    document = make_document()

    parsed = ParsedDocument(
        document=document,
        pages=[
            ParsedPage(
                page_number=1,
                text="Electrical characteristics",
            ),
        ],
    )

    assert parsed.document.document_id == "DOC-001"
    assert parsed.document.title == "Sample Datasheet"
    assert parsed.document.manufacturer == "Texas Instruments"
    assert parsed.document.mpn == "TPS7A4901"


def test_parsed_document_preserves_page_order() -> None:
    parsed = ParsedDocument(
        document=make_document(),
        pages=[
            ParsedPage(
                page_number=1,
                text="Page one",
            ),
            ParsedPage(
                page_number=2,
                text="Page two",
            ),
            ParsedPage(
                page_number=3,
                text="Page three",
            ),
        ],
    )

    assert [page.page_number for page in parsed.pages] == [
        1,
        2,
        3,
    ]


def test_parsed_document_text_preserves_page_order() -> None:
    parsed = ParsedDocument(
        document=make_document(),
        pages=[
            ParsedPage(
                page_number=1,
                text="Page one",
            ),
            ParsedPage(
                page_number=2,
                text="Page two",
            ),
            ParsedPage(
                page_number=3,
                text="Page three",
            ),
        ],
    )

    assert parsed.text == (
        "Page one\n\n"
        "Page two\n\n"
        "Page three"
    )


def test_parsed_document_text_ignores_empty_pages() -> None:
    parsed = ParsedDocument(
        document=make_document(),
        pages=[
            ParsedPage(
                page_number=1,
                text="Page one",
            ),
            ParsedPage(
                page_number=2,
                text="   ",
            ),
            ParsedPage(
                page_number=3,
                text="Page three",
            ),
        ],
    )

    assert parsed.text == (
        "Page one\n\n"
        "Page three"
    )


def test_empty_parsed_document_has_empty_text() -> None:
    parsed = ParsedDocument(
        document=make_document(),
        pages=[],
    )

    assert parsed.text == ""


def test_document_loader_is_abstract() -> None:
    import inspect

    assert inspect.isabstract(DocumentLoader)


def test_document_loader_supports_extension() -> None:
    class TestLoader(DocumentLoader):
        supported_extensions = {".pdf"}

        def load(
            self,
            file_path: Path,
        ) -> ParsedDocument:
            return ParsedDocument(
                document=make_document(),
                pages=[],
            )

    loader = TestLoader()

    assert loader.supports(".pdf")
    assert loader.supports(".PDF")
    assert not loader.supports(".xlsx")


def test_document_loader_load_returns_parsed_document() -> None:
    class TestLoader(DocumentLoader):
        supported_extensions = {".pdf"}

        def load(
            self,
            file_path: Path,
        ) -> ParsedDocument:
            return ParsedDocument(
                document=make_document(),
                pages=[
                    ParsedPage(
                        page_number=1,
                        text="Sample PDF content",
                    ),
                ],
            )

    loader = TestLoader()

    result = loader.load(
        Path("sample.pdf"),
    )

    assert isinstance(result, ParsedDocument)
    assert result.document.document_id == "DOC-001"
    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
