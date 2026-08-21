import pytest

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.scoring import (
    SupplierScorer,
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


def test_scorer_requires_positive_quantity():
    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        SupplierScorer(quantity=0)


def test_scorer_returns_100_for_ideal_supplier():
    quote = make_quote(
        supplier="digikey",
        unit_price=1.00,
        quantity_available=10000,
        moq=1,
        order_multiple=1,
        lead_time_days=1,
    )

    scorer = SupplierScorer(quantity=100)

    result = scorer.score(
        quote,
        quotes=[quote],
    )

    assert result.supplier == "digikey"
    assert result.total_score == 100


def test_price_is_part_of_supplier_score():
    cheap = make_quote(
        supplier="cheap",
        unit_price=1.00,
        quantity_available=5000,
        lead_time_days=5,
    )

    expensive = make_quote(
        supplier="expensive",
        unit_price=2.00,
        quantity_available=5000,
        lead_time_days=5,
    )

    scorer = SupplierScorer(quantity=100)

    cheap_score = scorer.score(
        cheap,
        quotes=[cheap, expensive],
    )

    expensive_score = scorer.score(
        expensive,
        quotes=[cheap, expensive],
    )

    assert (
        cheap_score.price_score
        > expensive_score.price_score
    )


def test_availability_is_part_of_supplier_score():
    high_stock = make_quote(
        supplier="high-stock",
        unit_price=1.00,
        quantity_available=10000,
    )

    low_stock = make_quote(
        supplier="low-stock",
        unit_price=1.00,
        quantity_available=100,
    )

    scorer = SupplierScorer(quantity=100)

    high_score = scorer.score(
        high_stock,
        quotes=[high_stock, low_stock],
    )

    low_score = scorer.score(
        low_stock,
        quotes=[high_stock, low_stock],
    )

    assert (
        high_score.availability_score
        > low_score.availability_score
    )


def test_lead_time_is_part_of_supplier_score():
    fast = make_quote(
        supplier="fast",
        unit_price=1.00,
        quantity_available=5000,
        lead_time_days=2,
    )

    slow = make_quote(
        supplier="slow",
        unit_price=1.00,
        quantity_available=5000,
        lead_time_days=20,
    )

    scorer = SupplierScorer(quantity=100)

    fast_score = scorer.score(
        fast,
        quotes=[fast, slow],
    )

    slow_score = scorer.score(
        slow,
        quotes=[fast, slow],
    )

    assert (
        fast_score.lead_time_score
        > slow_score.lead_time_score
    )


def test_moq_penalizes_supplier_that_cannot_meet_quantity():
    suitable = make_quote(
        supplier="suitable",
        unit_price=1.00,
        quantity_available=5000,
        moq=10,
    )

    unsuitable = make_quote(
        supplier="unsuitable",
        unit_price=1.00,
        quantity_available=5000,
        moq=500,
    )

    scorer = SupplierScorer(quantity=100)

    suitable_score = scorer.score(
        suitable,
        quotes=[suitable, unsuitable],
    )

    unsuitable_score = scorer.score(
        unsuitable,
        quotes=[suitable, unsuitable],
    )

    assert (
        suitable_score.moq_score
        > unsuitable_score.moq_score
    )


def test_order_multiple_penalizes_incompatible_quantity():
    compatible = make_quote(
        supplier="compatible",
        unit_price=1.00,
        quantity_available=5000,
        order_multiple=10,
    )

    incompatible = make_quote(
        supplier="incompatible",
        unit_price=1.00,
        quantity_available=5000,
        order_multiple=64,
    )

    scorer = SupplierScorer(quantity=100)

    compatible_score = scorer.score(
        compatible,
        quotes=[compatible, incompatible],
    )

    incompatible_score = scorer.score(
        incompatible,
        quotes=[compatible, incompatible],
    )

    assert (
        compatible_score.order_multiple_score
        > incompatible_score.order_multiple_score
    )


def test_score_is_bounded_between_zero_and_hundred():
    quote = make_quote(
        supplier="test",
        unit_price=1.50,
        quantity_available=1000,
        moq=10,
        order_multiple=10,
        lead_time_days=10,
    )

    scorer = SupplierScorer(quantity=100)

    result = scorer.score(
        quote,
        quotes=[quote],
    )

    assert 0 <= result.total_score <= 100