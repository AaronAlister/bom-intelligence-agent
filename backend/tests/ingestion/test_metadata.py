from pathlib import Path

from backend.app.ingestion.metadata import (
    extract_metadata,
    infer_from_filename,
)


def test_filename_revision_detection():

    file_path = Path(
        "Power_Control_Board_RevA.xlsx"
    )

    product, revision = infer_from_filename(
        file_path
    )

    assert product == "Power Control Board"

    assert revision == "A"


def test_filename_version_detection():

    file_path = Path(
        "Motor_Controller_v3.xlsx"
    )

    product, revision = infer_from_filename(
        file_path
    )

    assert product == "Motor Controller"

    assert revision == "3"


def test_explicit_metadata_has_priority():

    file_path = Path(
        "Power_Control_Board_RevA.xlsx"
    )

    product, revision = extract_metadata(
        file_path=file_path,
        records=[],
        product="Main Controller",
        revision="Rev-B",
    )

    assert product == "Main Controller"

    assert revision == "Rev-B"


def test_structured_metadata_has_priority_over_filename():

    file_path = Path(
        "Power_Control_Board_RevA.xlsx"
    )

    records = [
        {
            "Product": "Motor Controller",
            "Revision": "Rev-C",
        }
    ]

    product, revision = extract_metadata(
        file_path=file_path,
        records=records,
    )

    assert product == "Motor Controller"

    assert revision == "Rev-C"


def test_filename_is_used_when_metadata_is_missing():

    file_path = Path(
        "Power_Control_Board_RevA.xlsx"
    )

    product, revision = extract_metadata(
        file_path=file_path,
        records=[],
    )

    assert product == "Power Control Board"

    assert revision == "A"