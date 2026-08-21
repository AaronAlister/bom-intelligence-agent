from backend.app.ingestion.detector import (
    detect_columns,
    normalize_column_name,
)


def test_normalize_column_name():
    assert normalize_column_name("Mfr P/N") == "mfr p n"

    assert normalize_column_name("MFR-P/N") == "mfr p n"

    assert normalize_column_name("  Quantity  ") == "quantity"


def test_detect_standard_columns():

    columns = [
        "MPN",
        "Manufacturer",
        "Description",
        "Category",
        "Package",
        "Quantity",
        "Reference Designators",
    ]

    detected = detect_columns(columns)

    assert detected["mpn"] == "MPN"
    assert detected["manufacturer"] == "Manufacturer"
    assert detected["description"] == "Description"
    assert detected["category"] == "Category"
    assert detected["package"] == "Package"
    assert detected["quantity"] == "Quantity"
    assert detected["reference_designators"] == "Reference Designators"


def test_detect_real_world_bom_columns():

    columns = [
        "Mfr P/N",
        "Mfg",
        "Part Description",
        "Qty",
        "RefDes",
    ]

    detected = detect_columns(columns)

    assert detected["mpn"] == "Mfr P/N"
    assert detected["manufacturer"] == "Mfg"
    assert detected["description"] == "Part Description"
    assert detected["quantity"] == "Qty"
    assert detected["reference_designators"] == "RefDes"


def test_missing_optional_columns():

    columns = [
        "Part Number",
        "Manufacturer",
        "Qty",
    ]

    detected = detect_columns(columns)

    assert detected["mpn"] == "Part Number"
    assert detected["manufacturer"] == "Manufacturer"
    assert detected["quantity"] == "Qty"

    assert detected["description"] is None
    assert detected["package"] is None