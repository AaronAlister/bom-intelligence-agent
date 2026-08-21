import pytest

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.selection import (
    SupplierSelector,
)


def make_quote(
    *,
    supplier: str,
    unit_price: float,
    quantity_available: int,
    moq: int = 1,
    order_multiple: int = 1,
    lead_time_days: int = 5,
) -> SupplierQuote:
    return SupplierQuote(
        supplier=supplier,
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=unit_price,
        currency="USD",
        quantity_available=quantity_available,
        moq=moq,
        order_multiple=order_multiple,
        lead_time_days=lead_time_days,
        source=supplier,
    )


def test_selector_requires_at_least_one_supplier():
    with pytest.raises(
        ValueError,
        match="At least one supplier quote",
    ):
        SupplierSelector(quantity=100).select([])


def test_selector_requires_positive_quantity():
    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        SupplierSelector(quantity=0)


def test_selector_returns_highest_scoring_supplier():
    cheap = make_quote(
        supplier="mouser",
        unit_price=1.00,
        quantity_available=5000,
        lead_time_days=5,
    )

    expensive = make_quote(
        supplier="arrow",
        unit_price=2.00,
        quantity_available=5000,
        lead_time_days=5,
    )

    result = SupplierSelector(
        quantity=100
    ).select(
        [cheap, expensive]
    )

    assert result.selected_supplier == "mouser"
    assert result.selected_score is not None
    assert result.selected_score.supplier == "mouser"


def test_selector_returns_all_suppliers_ranked():
    mouser = make_quote(
        supplier="mouser",
        unit_price=1.00,
        quantity_available=5000,
    )

    arrow = make_quote(
        supplier="arrow",
        unit_price=1.20,
        quantity_available=4000,
    )

    digikey = make_quote(
        supplier="digikey",
        unit_price=1.50,
        quantity_available=3000,
    )

    result = SupplierSelector(
        quantity=100
    ).select(
        [mouser, arrow, digikey]
    )

    assert len(result.ranked_suppliers) == 3

    scores = [
        item.total_score
        for item in result.ranked_suppliers
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_selector_excludes_supplier_that_cannot_meet_moq():
    suitable = make_quote(
        supplier="mouser",
        unit_price=1.20,
        quantity_available=5000,
        moq=10,
    )

    unsuitable = make_quote(
        supplier="arrow",
        unit_price=0.50,
        quantity_available=5000,
        moq=500,
    )

    result = SupplierSelector(
        quantity=100
    ).select(
        [suitable, unsuitable]
    )

    assert (
        result.selected_supplier
        == "mouser"
    )


def test_selector_excludes_supplier_without_enough_inventory():
    available = make_quote(
        supplier="mouser",
        unit_price=1.20,
        quantity_available=1000,
    )

    insufficient = make_quote(
        supplier="arrow",
        unit_price=0.50,
        quantity_available=50,
    )

    result = SupplierSelector(
        quantity=100
    ).select(
        [available, insufficient]
    )

    assert (
        result.selected_supplier
        == "mouser"
    )


def test_selector_exposes_component_scores():
    quote = make_quote(
        supplier="digikey",
        unit_price=1.00,
        quantity_available=5000,
        moq=10,
        order_multiple=10,
        lead_time_days=2,
    )

    result = SupplierSelector(
        quantity=100
    ).select(
        [quote]
    )

    score = result.selected_score

    assert score is not None
    assert score.supplier == "digikey"
    assert score.price_score > 0
    assert score.availability_score > 0
    assert score.lead_time_score > 0
    assert score.moq_score > 0
    assert score.order_multiple_score > 0


def test_selector_handles_tie_deterministically():
    arrow = make_quote(
        supplier="arrow",
        unit_price=1.00,
        quantity_available=5000,
        lead_time_days=5,
    )

    mouser = make_quote(
        supplier="mouser",
        unit_price=1.00,
        quantity_available=5000,
        lead_time_days=5,
    )

    result = SupplierSelector(
        quantity=100
    ).select(
        [arrow, mouser]
    )

    assert result.selected_supplier == "arrow"


def test_selector_provides_recommendation_reason():
    quote = make_quote(
        supplier="digikey",
        unit_price=1.00,
        quantity_available=5000,
        moq=10,
        order_multiple=10,
        lead_time_days=2,
    )

    result = SupplierSelector(
        quantity=100
    ).select(
        [quote]
    )

    assert result.recommendation_reason
    assert isinstance(
        result.recommendation_reason,
        str,
    )