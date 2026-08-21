from backend.app.ingestion.deduplicator import (
    deduplicate_components,
)


def test_deduplicate_same_mpn():

    components = [
        {
            "mpn": "LM358DR",
            "manufacturer": "Texas Instruments",
            "quantity": 2,
            "reference_designators": [
                "U1",
                "U2",
            ],
        },
        {
            "mpn": "LM358DR",
            "manufacturer": "Texas Instruments",
            "quantity": 2,
            "reference_designators": [
                "U3",
                "U4",
            ],
        },
    ]

    result = deduplicate_components(
        components
    )

    assert len(result) == 1

    assert result[0]["mpn"] == "LM358DR"

    assert result[0]["quantity"] == 4

    assert result[0]["reference_designators"] == [
        "U1",
        "U2",
        "U3",
        "U4",
    ]


def test_different_mpns_are_preserved():

    components = [
        {
            "mpn": "LM358DR",
            "manufacturer": "Texas Instruments",
            "quantity": 2,
            "reference_designators": ["U1"],
        },
        {
            "mpn": "STM32F401",
            "manufacturer": "STMicroelectronics",
            "quantity": 1,
            "reference_designators": ["U2"],
        },
    ]

    result = deduplicate_components(
        components
    )

    assert len(result) == 2


def test_duplicate_references_are_removed():

    components = [
        {
            "mpn": "LM358DR",
            "quantity": 2,
            "reference_designators": [
                "U1",
                "U2",
            ],
        },
        {
            "mpn": "LM358DR",
            "quantity": 1,
            "reference_designators": [
                "U2",
                "U3",
            ],
        },
    ]

    result = deduplicate_components(
        components
    )

    assert result[0]["quantity"] == 3

    assert result[0]["reference_designators"] == [
        "U1",
        "U2",
        "U3",
    ]


def test_missing_metadata_is_filled():

    components = [
        {
            "mpn": "LM358DR",
            "manufacturer": None,
            "description": None,
            "quantity": 2,
            "reference_designators": [],
        },
        {
            "mpn": "LM358DR",
            "manufacturer": "Texas Instruments",
            "description": "Dual op amp",
            "quantity": 1,
            "reference_designators": [],
        },
    ]

    result = deduplicate_components(
        components
    )

    assert len(result) == 1

    assert result[0]["manufacturer"] == (
        "Texas Instruments"
    )

    assert result[0]["description"] == (
        "Dual op amp"
    )

    assert result[0]["quantity"] == 3