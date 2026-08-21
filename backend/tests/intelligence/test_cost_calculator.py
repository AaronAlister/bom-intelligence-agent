import pytest

from backend.app.intelligence.availability.supplier.models import (
    PriceBreak,
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.cost import (
    ComponentCostCalculator,
)


def make_quote() -> SupplierQuote:
    return SupplierQuote(
        supplier="mouser",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=2.40,
        currency="USD",
        quantity_available=5000,
        moq=None,
        order_multiple=None,
        lead_time_days=14,
        price_breaks=[
            PriceBreak(
                min_quantity=1,
                unit_price=2.40,
                currency="USD",
            ),
            PriceBreak(
                min_quantity=10,
                unit_price=2.10,
                currency="USD",
            ),
            PriceBreak(
                min_quantity=100,
                unit_price=1.72,
                currency="USD",
            ),
        ],
        source="mouser",
    )


def test_calculator_requires_positive_quantity():
    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        ComponentCostCalculator(
            quantity=0
        )


def test_calculator_uses_applicable_price_break():
    quote = make_quote()

    result = ComponentCostCalculator(
        quantity=100
    ).calculate(quote)

    assert result.supplier == "mouser"
    assert result.mpn == "LM358DR"
    assert result.quantity == 100

    assert result.unit_price == 1.72
    assert result.total_cost == 172.00
    assert result.currency == "USD"


def test_calculator_uses_highest_applicable_tier():
    quote = make_quote()

    result = ComponentCostCalculator(
        quantity=500
    ).calculate(quote)

    assert result.unit_price == 1.72
    assert result.total_cost == 860.00


def test_calculator_uses_first_tier_when_quantity_below_next_break():
    quote = make_quote()

    result = ComponentCostCalculator(
        quantity=5
    ).calculate(quote)

    assert result.unit_price == 2.40
    assert result.total_cost == 12.00


def test_calculator_uses_quote_unit_price_without_price_breaks():
    quote = SupplierQuote(
        supplier="arrow",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=2.00,
        currency="USD",
        quantity_available=5000,
        source="arrow",
    )

    result = ComponentCostCalculator(
        quantity=100
    ).calculate(quote)

    assert result.unit_price == 2.00
    assert result.total_cost == 200.00
    assert result.currency == "USD"


def test_calculator_returns_none_when_no_price_available():
    quote = SupplierQuote(
        supplier="arrow",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        quantity_available=5000,
        source="arrow",
    )

    result = ComponentCostCalculator(
        quantity=100
    ).calculate(quote)

    assert result.unit_price is None
    assert result.total_cost is None


def test_calculator_rejects_insufficient_inventory():
    quote = SupplierQuote(
        supplier="mouser",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=2.00,
        currency="USD",
        quantity_available=50,
        source="mouser",
    )

    with pytest.raises(
        ValueError,
        match="cannot fulfill",
    ):
        ComponentCostCalculator(
            quantity=100
        ).calculate(quote)


def test_calculator_rejects_moq_violation():
    quote = SupplierQuote(
        supplier="mouser",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=2.00,
        currency="USD",
        quantity_available=5000,
        moq=500,
        source="mouser",
    )

    with pytest.raises(
        ValueError,
        match="MOQ",
    ):
        ComponentCostCalculator(
            quantity=100
        ).calculate(quote)


def test_calculator_rejects_order_multiple_violation():
    quote = SupplierQuote(
        supplier="mouser",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=2.00,
        currency="USD",
        quantity_available=5000,
        order_multiple=64,
        source="mouser",
    )

    with pytest.raises(
        ValueError,
        match="order multiple",
    ):
        ComponentCostCalculator(
            quantity=100
        ).calculate(quote)