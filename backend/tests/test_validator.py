from backend.app.ingestion.validator import (
    validate_bom_structure,
    validate_component,
)


def test_valid_component():

    component = {
        "mpn": "LM358DR",
        "manufacturer": "Texas Instruments",
        "description": "Dual operational amplifier",
        "category": "Analog IC",
        "package": "SOIC-8",
        "quantity": 4,
        "reference_designators": [
            "U1",
            "U2",
        ],
    }

    errors = validate_component(component)

    assert errors == []


def test_missing_mpn():

    component = {
        "mpn": None,
        "manufacturer": "Texas Instruments",
        "quantity": 4,
    }

    errors = validate_component(component)

    assert len(errors) == 1
    assert errors[0].field == "mpn"
    assert errors[0].severity == "error"


def test_missing_quantity():

    component = {
        "mpn": "LM358DR",
        "manufacturer": "Texas Instruments",
        "quantity": None,
    }

    errors = validate_component(component)

    assert len(errors) == 1
    assert errors[0].field == "quantity"
    assert errors[0].severity == "error"


def test_invalid_quantity():

    component = {
        "mpn": "LM358DR",
        "manufacturer": "Texas Instruments",
        "quantity": 0,
    }

    errors = validate_component(component)

    assert len(errors) == 1
    assert errors[0].field == "quantity"
    assert errors[0].severity == "error"


def test_negative_quantity():

    component = {
        "mpn": "LM358DR",
        "manufacturer": "Texas Instruments",
        "quantity": -5,
    }

    errors = validate_component(component)

    assert len(errors) == 1
    assert errors[0].field == "quantity"


def test_missing_manufacturer_is_warning():

    component = {
        "mpn": "LM358DR",
        "manufacturer": None,
        "quantity": 4,
    }

    errors = validate_component(component)

    assert len(errors) == 1
    assert errors[0].field == "manufacturer"
    assert errors[0].severity == "warning"


def test_collect_multiple_errors():

    component = {
        "mpn": None,
        "manufacturer": None,
        "quantity": -5,
    }

    errors = validate_component(component)

    assert len(errors) == 3

    assert errors[0].field == "mpn"
    assert errors[1].field == "quantity"
    assert errors[2].field == "manufacturer"

def test_valid_bom_structure():

    columns = [
        "MPN",
        "Quantity",
        "Manufacturer",
        "Description",
    ]

    errors = validate_bom_structure(
        columns
    )

    assert errors == []


def test_missing_mpn_column():

    columns = [
        "Manufacturer",
        "Quantity",
        "Description",
    ]

    errors = validate_bom_structure(
        columns
    )

    assert len(errors) == 1

    assert errors[0].field == "mpn"

    assert errors[0].severity == "error"


def test_missing_quantity_column():

    columns = [
        "MPN",
        "Manufacturer",
        "Description",
    ]

    errors = validate_bom_structure(
        columns
    )

    assert len(errors) == 1

    assert errors[0].field == "quantity"

    assert errors[0].severity == "error"


def test_missing_required_columns():

    columns = [
        "Description",
        "Package",
    ]

    errors = validate_bom_structure(
        columns
    )

    assert len(errors) == 2

    assert {
        error.field
        for error in errors
    } == {
        "mpn",
        "quantity",
    }


def test_optional_columns_are_not_required():

    columns = [
        "MPN",
        "Quantity",
    ]

    errors = validate_bom_structure(
        columns
    )

    assert errors == []

def test_ambiguous_required_column_is_rejected():

    columns = [
        "Part Number",
        "Manufacturer Part Number",
        "Quantity",
    ]

    errors = validate_bom_structure(
        columns
    )

    assert len(errors) == 1

    assert errors[0].field == "mpn"

    assert errors[0].severity == "error"

    assert "ambiguous" in errors[0].message.lower()