import pytest

from backend.app.intelligence.availability.supplier.comparison import (
    CostComparison,
    CostComparisonService,
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
        mpn="LM358DR",
        unit_price=1.85,
        currency="USD",
        quantity_available=5000,
        source="arrow",
    )


def make_digikey_quote() -> SupplierQuote:
    return SupplierQuote(
        supplier="digikey",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=1.60,
        currency="USD",
        quantity_available=8100,
        source="digikey",
    )


def test_comparison_requires_at_least_one_quote():
    with pytest.raises(
        ValueError,
        match="At least one supplier quote",
    ):
        CostComparisonService([])


def test_comparison_selects_lowest_cost_supplier():
    service = CostComparisonService(
        [
            make_mouser_quote(),
            make_arrow_quote(),
            make_digikey_quote(),
        ]
    )

    result = service.compare(
        quantity=100,
    )

    assert isinstance(
        result,
        CostComparison,
    )

    assert result.mpn == "LM358DR"
    assert result.quantity == 100

    assert result.best_supplier == "digikey"
    assert result.best_unit_price == 1.60
    assert result.best_total_cost == 160.00
    assert result.currency == "USD"


def test_comparison_calculates_potential_savings():
    service = CostComparisonService(
        [
            make_mouser_quote(),
            make_arrow_quote(),
            make_digikey_quote(),
        ]
    )

    result = service.compare(
        quantity=100,
    )

    assert result.highest_total_cost == 185.00
    assert result.best_total_cost == 160.00

    assert result.potential_savings == 25.00

    assert (
        result.potential_savings_percent
        == pytest.approx(
            13.513514,
            rel=1e-5,
        )
    )


def test_comparison_applies_price_breaks_before_comparing():
    service = CostComparisonService(
        [
            make_mouser_quote(),
            make_arrow_quote(),
        ]
    )

    result = service.compare(
        quantity=100,
    )

    # Mouser becomes $1.72 at quantity 100.
    # Arrow remains $1.85.
    assert result.best_supplier == "mouser"
    assert result.best_unit_price == 1.72
    assert result.best_total_cost == 172.00


def test_comparison_returns_all_supplier_costs():
    service = CostComparisonService(
        [
            make_mouser_quote(),
            make_arrow_quote(),
            make_digikey_quote(),
        ]
    )

    result = service.compare(
        quantity=100,
    )

    assert len(result.options) == 3

    assert [
        option.supplier
        for option in result.options
    ] == [
        "mouser",
        "arrow",
        "digikey",
    ]

    assert [
        option.total_cost
        for option in result.options
    ] == [
        172.00,
        185.00,
        160.00,
    ]


def test_comparison_rejects_mixed_currencies():
    euro_quote = SupplierQuote(
        supplier="arrow",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=1.50,
        currency="EUR",
        quantity_available=5000,
        source="arrow",
    )

    service = CostComparisonService(
        [
            make_mouser_quote(),
            euro_quote,
        ]
    )

    with pytest.raises(
        ValueError,
        match="currency",
    ):
        service.compare(
            quantity=100,
        )


def test_comparison_ignores_supplier_without_price():
    unavailable_price = SupplierQuote(
        supplier="arrow",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        currency="USD",
        quantity_available=5000,
        source="arrow",
    )

    service = CostComparisonService(
        [
            unavailable_price,
            make_digikey_quote(),
        ]
    )

    result = service.compare(
        quantity=100,
    )

    assert result.best_supplier == "digikey"
    assert len(result.options) == 2

    assert (
        result.options[0].total_cost
        is None
    )

    assert (
        result.options[1].total_cost
        == 160.00
    )


def test_comparison_fails_when_no_supplier_has_price():
    first = SupplierQuote(
        supplier="mouser",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        currency="USD",
        source="mouser",
    )

    second = SupplierQuote(
        supplier="arrow",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        currency="USD",
        source="arrow",
    )

    service = CostComparisonService(
        [
            first,
            second,
        ]
    )

    with pytest.raises(
        ValueError,
        match="No supplier has a calculable cost",
    ):
        service.compare(
            quantity=100,
        )


def test_comparison_rejects_invalid_quantity():
    service = CostComparisonService(
        [
            make_mouser_quote(),
        ]
    )

    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        service.compare(
            quantity=0,
        )