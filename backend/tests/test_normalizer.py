from backend.app.ingestion.normalizer import (
    normalize_component,
    normalize_manufacturer,
    normalize_mpn,
    normalize_quantity,
    normalize_reference_designators,
    normalize_text,
)


def test_normalize_text():

    assert normalize_text("  hello  ") == "hello"

    assert normalize_text("") is None

    assert normalize_text("   ") is None

    assert normalize_text(None) is None


def test_normalize_mpn():

    assert normalize_mpn("  LM358DR  ") == "LM358DR"

    assert normalize_mpn(None) is None


def test_normalize_manufacturer():

    assert (
        normalize_manufacturer(
            "  Texas   Instruments, Inc.  "
        )
        == "Texas Instruments, Inc."
    )


def test_normalize_quantity():

    assert normalize_quantity("4") == 4

    assert normalize_quantity("4.0") == 4

    assert normalize_quantity(4) == 4

    assert normalize_quantity(4.0) == 4

    assert normalize_quantity("4.5") is None

    assert normalize_quantity("abc") is None

    assert normalize_quantity(None) is None


def test_normalize_reference_designators():

    value = "U1, U2; U3, U4"

    assert normalize_reference_designators(value) == [
        "U1",
        "U2",
        "U3",
        "U4",
    ]


def test_normalize_component():

    raw_record = {
        "Mfr P/N": "  LM358DR  ",
        "Mfg": "  Texas   Instruments, Inc.  ",
        "Part Description": " Dual operational amplifier ",
        "Qty": "4.0",
        "RefDes": "U1, U2, U3, U4",
    }

    column_mapping = {
        "mpn": "Mfr P/N",
        "manufacturer": "Mfg",
        "description": "Part Description",
        "category": None,
        "package": None,
        "quantity": "Qty",
        "reference_designators": "RefDes",
    }

    result = normalize_component(
        raw_record,
        column_mapping,
    )

    assert result == {
        "mpn": "LM358DR",
        "manufacturer": "Texas Instruments, Inc.",
        "description": "Dual operational amplifier",
        "category": None,
        "package": None,
        "quantity": 4,
        "reference_designators": [
            "U1",
            "U2",
            "U3",
            "U4",
        ],
    }