from pathlib import Path

import pytest
import json

from backend.app.ingestion.parsers import get_parser


FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "boms"
)


@pytest.mark.parametrize(
    ("filename", "extension"),
    [
        ("sample.csv", ".csv"),
        ("sample.tsv", ".tsv"),
        ("sample.xls", ".xls"),
        ("sample.xlsx", ".xlsx"),
        ("sample.json", ".json"),
        ("sample.xml", ".xml"),
    ],
)
def test_fixture_parser_selection(
    filename: str,
    extension: str,
):
    file_path = FIXTURE_DIR / filename

    assert file_path.exists()

    parser = get_parser(extension)

    records = parser.parse(file_path)

    assert records

    assert isinstance(records, list)

    assert all(
        isinstance(record, dict)
        for record in records
    )


def test_csv_fixture():

    file_path = FIXTURE_DIR / "sample.csv"

    parser = get_parser(".csv")

    records = parser.parse(file_path)

    assert len(records) == 4

    assert records[0]["Mfr P/N"] == "LM358DR"


def test_tsv_fixture():

    file_path = FIXTURE_DIR / "sample.tsv"

    parser = get_parser(".tsv")

    records = parser.parse(file_path)

    assert len(records) == 4

    assert records[0]["Mfr P/N"] == "LM358DR"


def test_xlsx_fixture():

    file_path = FIXTURE_DIR / "sample.xlsx"

    parser = get_parser(".xlsx")

    records = parser.parse(file_path)

    assert len(records) == 4

    assert records[0]["Mfr P/N"] == "LM358DR"

def test_xls_fixture():

    file_path = FIXTURE_DIR / "sample.xls"

    parser = get_parser(".xls")

    records = parser.parse(file_path)

    assert len(records) == 3

    assert records[0]["Mfr P/N"] == "LM358DR"


def test_json_fixture():

    file_path = FIXTURE_DIR / "sample.json"

    parser = get_parser(".json")

    records = parser.parse(file_path)

    assert len(records) == 4

    assert records[0]["Mfr P/N"] == "LM358DR"


def test_xml_fixture():

    file_path = FIXTURE_DIR / "sample.xml"

    parser = get_parser(".xml")

    records = parser.parse(file_path)

    assert records

    assert any(
        record.get("Mfr_P_N") == "LM358DR"
        for record in records
    )

def test_json_unsupported_structure(
    tmp_path: Path,
):

    file_path = tmp_path / "invalid.json"

    file_path.write_text(
        json.dumps("not a BOM"),
        encoding="utf-8",
    )

    parser = get_parser(".json")

    with pytest.raises(
        ValueError,
        match="Unsupported JSON BOM structure",
    ):
        parser.parse(file_path)

def test_xml_with_no_component_records(
    tmp_path: Path,
):

    file_path = tmp_path / "empty_structure.xml"

    file_path.write_text(
        """
        <bom>
            <metadata>
                <product>Test Board</product>
                <revision>A</revision>
            </metadata>
        </bom>
        """,
        encoding="utf-8",
    )

    parser = get_parser(".xml")

    records = parser.parse(
        file_path
    )

    assert records == []