from pathlib import Path

import fitz
import pytest

from backend.app.rag.documents.pdf import PDFDocumentLoader
from backend.app.rag.documents.models import ParsedDocument


def create_pdf(
    file_path: Path,
    pages: list[str],
) -> None:
    """
    Create a small text PDF for parser testing.
    """

    document = fitz.open()

    try:
        for page_text in pages:
            page = document.new_page()
            page.insert_text(
                (72, 72),
                page_text,
            )

        document.save(file_path)
    finally:
        document.close()


def test_pdf_loader_supports_pdf_extension() -> None:
    loader = PDFDocumentLoader()

    assert loader.supports(".pdf")
    assert loader.supports(".PDF")
    assert not loader.supports(".xlsx")


def test_pdf_loader_extracts_single_page(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "sample_datasheet.pdf"

    create_pdf(
        pdf_path,
        [
            "Input voltage: 3 V to 36 V",
        ],
    )

    loader = PDFDocumentLoader()

    result = loader.load(pdf_path)

    assert isinstance(result, ParsedDocument)
    assert result.document.title == "sample_datasheet"
    assert result.document.source == "sample_datasheet.pdf"
    assert result.document.metadata["document_type"] == "pdf"
    assert result.document.metadata["page_count"] == 1

    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
    assert "Input voltage: 3 V to 36 V" in result.pages[0].text


def test_pdf_loader_extracts_multiple_pages(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "multi_page.pdf"

    create_pdf(
        pdf_path,
        [
            "Electrical characteristics",
            "Input voltage: 3 V to 36 V",
            "Operating temperature: -40 C to 125 C",
        ],
    )

    loader = PDFDocumentLoader()

    result = loader.load(pdf_path)

    assert len(result.pages) == 3

    assert result.pages[0].page_number == 1
    assert result.pages[1].page_number == 2
    assert result.pages[2].page_number == 3

    assert "Electrical characteristics" in result.pages[0].text
    assert "Input voltage: 3 V to 36 V" in result.pages[1].text
    assert (
        "Operating temperature: -40 C to 125 C"
        in result.pages[2].text
    )


def test_pdf_loader_preserves_page_metadata(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "metadata_test.pdf"

    create_pdf(
        pdf_path,
        [
            "Page one",
            "Page two",
        ],
    )

    loader = PDFDocumentLoader()

    result = loader.load(pdf_path)

    assert result.pages[0].metadata["page_number"] == 1
    assert result.pages[1].metadata["page_number"] == 2


def test_pdf_loader_creates_deterministic_document_id(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.pdf"
    second_path = tmp_path / "second.pdf"

    create_pdf(
        first_path,
        [
            "Same document content",
        ],
    )

    first_bytes = first_path.read_bytes()
    second_path.write_bytes(first_bytes)

    loader = PDFDocumentLoader()

    first_result = loader.load(first_path)
    second_result = loader.load(second_path)

    assert (
        first_result.document.document_id
        == second_result.document.document_id
    )


def test_pdf_loader_rejects_missing_file(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "missing.pdf"

    loader = PDFDocumentLoader()

    with pytest.raises(FileNotFoundError):
        loader.load(pdf_path)


def test_pdf_loader_rejects_non_pdf_extension(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "document.txt"
    file_path.write_text(
        "Not a PDF",
        encoding="utf-8",
    )

    loader = PDFDocumentLoader()

    with pytest.raises(ValueError):
        loader.load(file_path)


def test_pdf_loader_rejects_corrupt_pdf(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(
        b"This is not a valid PDF."
    )

    loader = PDFDocumentLoader()

    with pytest.raises(RuntimeError):
        loader.load(pdf_path)


def test_pdf_loader_rejects_textless_pdf(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "textless.pdf"

    document = fitz.open()

    try:
        document.new_page()
        document.save(pdf_path)
    finally:
        document.close()

    loader = PDFDocumentLoader()

    with pytest.raises(ValueError):
        loader.load(pdf_path)


def test_pdf_loader_uses_filename_as_title(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "TPS7A4901_Datasheet.pdf"

    create_pdf(
        pdf_path,
        [
            "TPS7A4901 Datasheet",
        ],
    )

    loader = PDFDocumentLoader()

    result = loader.load(pdf_path)

    assert (
        result.document.title
        == "TPS7A4901_Datasheet"
    )

def test_pdf_loader_cleans_extracted_text(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "cleaning_test.pdf"

    create_pdf(
        pdf_path,
        [
            "Input Voltage: 3 V to 36 V\n\n\n"
            "Output Current: 300 mA",
        ],
    )

    loader = PDFDocumentLoader()

    result = loader.load(pdf_path)

    page_text = result.pages[0].text

    assert "Input Voltage: 3 V to 36 V" in page_text
    assert "Output Current: 300 mA" in page_text
    assert "\n\n\n" not in page_text
