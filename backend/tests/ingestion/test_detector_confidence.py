from backend.app.ingestion.detector import (
    detect_columns_with_confidence,
)


def test_exact_mpn_match_has_high_confidence():

    result = detect_columns_with_confidence(
        [
            "MPN",
            "Manufacturer",
            "Quantity",
        ]
    )

    detection = result["mpn"]

    assert detection.column == "MPN"

    assert detection.confidence == 1.0

    assert detection.ambiguous is False

def test_mfr_part_number_has_high_confidence():

    result = detect_columns_with_confidence(
        [
            "Mfr P/N",
            "Mfg",
            "Qty",
        ]
    )

    assert result["mpn"].column == "Mfr P/N"

    assert result["mpn"].confidence == 1.0

    assert result["manufacturer"].column == "Mfg"

    assert result["quantity"].column == "Qty"

def test_missing_column_returns_none():

    result = detect_columns_with_confidence(
        [
            "Description",
            "Category",
        ]
    )

    detection = result["mpn"]

    assert detection.column is None

    assert detection.confidence == 0.0

    assert detection.ambiguous is False

def test_ambiguous_mpn_candidates():

    result = detect_columns_with_confidence(
        [
            "Part Number",
            "Manufacturer Part Number",
        ]
    )

    detection = result["mpn"]

    assert detection.ambiguous is True

    assert len(detection.candidates) >= 2

def test_low_confidence_column_is_not_auto_mapped():

    result = detect_columns_with_confidence(
        [
            "Component Identifier",
        ]
    )

    detection = result["mpn"]

    assert detection.column is None

    assert detection.confidence < 0.75