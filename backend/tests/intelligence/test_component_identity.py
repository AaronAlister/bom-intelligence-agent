from backend.app.intelligence.component_identity import (
    component_identity_key,
    normalize_component_identity,
)


def test_normalize_component_identity():
    result = normalize_component_identity(
        mpn="  LM358-N  ",
        manufacturer=" Texas   Instruments ",
    )

    assert result == {
        "normalized_mpn": "LM358-N",
        "normalized_manufacturer": "Texas Instruments",
    }


def test_component_identity_key():
    result = component_identity_key(
        mpn="  ABC123  ",
        manufacturer=" Acme   Corp ",
    )

    assert result == (
        "ABC123",
        "Acme Corp",
    )


def test_identity_handles_missing_values():
    result = normalize_component_identity(
        mpn=None,
        manufacturer=None,
    )

    assert result == {
        "normalized_mpn": None,
        "normalized_manufacturer": None,
    }