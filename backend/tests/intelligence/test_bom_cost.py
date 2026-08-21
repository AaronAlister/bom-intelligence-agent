import pytest

from backend.app.intelligence.availability.supplier.bom_cost import (
    BOMCostCalculator,
    BOMComponentCost,
)
from backend.app.intelligence.availability.supplier.models import (
    PriceBreak,
    SupplierQuote,
)


def make_mouser_quote() -> SupplierQuote:
    return SupplierQuote(
        supplier="mouser",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=2.40,
        currency="USD",
        quantity_available=5000,
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


def make_arrow_quote() -> SupplierQuote:
    return SupplierQuote(
        supplier="arrow",
        manufacturer="Texas Instruments",
        mpn="NE555D",
        unit_price=1.50,
        currency="USD",
        quantity_available=3000,
        source="arrow",
    )


def test_bom_cost_calculator_requires_components():
    with pytest.raises(
        ValueError,
        match="At least one BOM component",
    ):
        BOMCostCalculator([])


def test_bom_cost_calculator_calculates_single_component():
    calculator = BOMCostCalculator(
        [
            (
                make_mouser_quote(),
                100,
            )
        ]
    )

    result = calculator.calculate()

    assert result.total_cost == 172.00
    assert result.currency == "USD"

    assert len(result.components) == 1

    component = result.components[0]

    assert isinstance(
        component,
        BOMComponentCost,
    )

    assert component.mpn == "LM358DR"
    assert component.supplier == "mouser"
    assert component.quantity == 100
    assert component.unit_price == 1.72
    assert component.total_cost == 172.00


def test_bom_cost_calculator_aggregates_multiple_components():
    calculator = BOMCostCalculator(
        [
            (
                make_mouser_quote(),
                100,
            ),
            (
                make_arrow_quote(),
                50,
            ),
        ]
    )

    result = calculator.calculate()

    assert len(result.components) == 2

    assert result.total_cost == 247.00
    assert result.currency == "USD"


def test_bom_cost_calculator_applies_price_breaks_per_component():
    calculator = BOMCostCalculator(
        [
            (
                make_mouser_quote(),
                5,
            ),
            (
                make_mouser_quote(),
                10,
            ),
            (
                make_mouser_quote(),
                100,
            ),
        ]
    )

    result = calculator.calculate()

    assert [
        component.unit_price
        for component in result.components
    ] == [
        2.40,
        2.10,
        1.72,
    ]

    assert result.total_cost == (
        12.00
        + 21.00
        + 172.00
    )


def test_bom_cost_calculator_rejects_non_positive_quantity():
    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        BOMCostCalculator(
            [
                (
                    make_mouser_quote(),
                    0,
                )
            ]
        )


def test_bom_cost_calculator_rejects_mixed_currencies():
    euro_quote = SupplierQuote(
        supplier="arrow",
        manufacturer="Texas Instruments",
        mpn="NE555D",
        unit_price=1.50,
        currency="EUR",
        quantity_available=3000,
        source="arrow",
    )

    calculator = BOMCostCalculator(
        [
            (
                make_mouser_quote(),
                100,
            ),
            (
                euro_quote,
                50,
            ),
        ]
    )

    with pytest.raises(
        ValueError,
        match="currency",
    ):
        calculator.calculate()


def test_bom_cost_calculator_returns_none_cost_when_price_missing():
    quote = SupplierQuote(
        supplier="arrow",
        manufacturer="Texas Instruments",
        mpn="NE555D",
        currency="USD",
        quantity_available=3000,
        source="arrow",
    )

    calculator = BOMCostCalculator(
        [
            (
                quote,
                50,
            )
        ]
    )

    result = calculator.calculate()

    assert len(result.components) == 1

    assert (
        result.components[0].unit_price
        is None
    )

    assert (
        result.components[0].total_cost
        is None
    )

    assert result.total_cost is None


def test_bom_cost_calculator_preserves_component_order():
    calculator = BOMCostCalculator(
        [
            (
                make_arrow_quote(),
                50,
            ),
            (
                make_mouser_quote(),
                100,
            ),
        ]
    )

    result = calculator.calculate()

    assert [
        component.mpn
        for component in result.components
    ] == [
        "NE555D",
        "LM358DR",
    ]


def test_bom_cost_calculator_exposes_component_breakdown():
    calculator = BOMCostCalculator(
        [
            (
                make_mouser_quote(),
                100,
            ),
            (
                make_arrow_quote(),
                50,
            ),
        ]
    )

    result = calculator.calculate()

    assert result.components[0].mpn == "LM358DR"
    assert result.components[0].total_cost == 172.00

    assert result.components[1].mpn == "NE555D"
    assert result.components[1].total_cost == 75.00