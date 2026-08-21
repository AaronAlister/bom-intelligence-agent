import pytest

from backend.app.intelligence.availability.supplier.models import (
    PriceBreak,
)
from backend.app.intelligence.availability.supplier.pricing import (
    select_price_break,
)


@pytest.fixture
def price_breaks():
    return [
        PriceBreak(
            min_quantity=1,
            max_quantity=9,
            unit_price=2.40,
            currency="USD",
        ),
        PriceBreak(
            min_quantity=10,
            max_quantity=99,
            unit_price=2.10,
            currency="USD",
        ),
        PriceBreak(
            min_quantity=100,
            unit_price=1.72,
            currency="USD",
        ),
    ]


def test_selects_first_tier(price_breaks):
    result = select_price_break(
        price_breaks,
        quantity=1,
    )

    assert result is not None
    assert result.min_quantity == 1
    assert result.unit_price == 2.40


def test_selects_middle_tier(price_breaks):
    result = select_price_break(
        price_breaks,
        quantity=50,
    )

    assert result is not None
    assert result.min_quantity == 10
    assert result.unit_price == 2.10


def test_selects_highest_applicable_tier(price_breaks):
    result = select_price_break(
        price_breaks,
        quantity=100,
    )

    assert result is not None
    assert result.min_quantity == 100
    assert result.unit_price == 1.72


def test_selects_highest_tier_for_large_quantity(
    price_breaks,
):
    result = select_price_break(
        price_breaks,
        quantity=1000,
    )

    assert result is not None
    assert result.min_quantity == 100
    assert result.unit_price == 1.72


def test_returns_none_when_no_tier_applies():
    price_breaks = [
        PriceBreak(
            min_quantity=100,
            max_quantity=199,
            unit_price=1.72,
            currency="USD",
        )
    ]

    result = select_price_break(
        price_breaks,
        quantity=50,
    )

    assert result is None


@pytest.mark.parametrize(
    "quantity",
    [0, -1, -100],
)
def test_rejects_non_positive_quantity(quantity):
    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        select_price_break([], quantity)