import pytest

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.recommendation import (
    ProcurementRecommendationService,
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


def test_recommendation_requires_positive_quantity():
    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        ProcurementRecommendationService(
            quantity=0
        )


def test_recommendation_requires_supplier_quotes():
    service = ProcurementRecommendationService(
        quantity=100
    )

    with pytest.raises(
        ValueError,
        match="At least one supplier quote",
    ):
        service.recommend([])


def test_recommendation_selects_best_supplier():
    mouser = make_quote(
        supplier="mouser",
        unit_price=1.00,
        quantity_available=5000,
        lead_time_days=5,
    )

    arrow = make_quote(
        supplier="arrow",
        unit_price=2.00,
        quantity_available=5000,
        lead_time_days=10,
    )

    service = ProcurementRecommendationService(
        quantity=100
    )

    result = service.recommend(
        [mouser, arrow]
    )

    assert result.action == "BUY"
    assert result.supplier == "mouser"
    assert result.score is not None
    assert result.score.supplier == "mouser"


def test_recommendation_contains_decision_factors():
    quote = make_quote(
        supplier="digikey",
        unit_price=1.00,
        quantity_available=5000,
        moq=10,
        order_multiple=10,
        lead_time_days=2,
    )

    service = ProcurementRecommendationService(
        quantity=100
    )

    result = service.recommend(
        [quote]
    )

    assert result.action == "BUY"
    assert result.supplier == "digikey"

    assert result.score is not None
    assert result.score.price_score > 0
    assert result.score.availability_score > 0
    assert result.score.lead_time_score > 0
    assert result.score.moq_score > 0
    assert result.score.order_multiple_score > 0


def test_recommendation_includes_alternative_suppliers():
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

    service = ProcurementRecommendationService(
        quantity=100
    )

    result = service.recommend(
        [mouser, arrow, digikey]
    )

    assert result.action == "BUY"
    assert result.supplier == "mouser"

    assert len(
        result.alternatives
    ) == 2

    assert [
        supplier.supplier
        for supplier in result.alternatives
    ] == [
        "arrow",
        "digikey",
    ]


def test_recommendation_returns_unavailable_when_no_supplier_can_fulfill():
    mouser = make_quote(
        supplier="mouser",
        unit_price=1.00,
        quantity_available=50,
    )

    arrow = make_quote(
        supplier="arrow",
        unit_price=1.20,
        quantity_available=75,
    )

    service = ProcurementRecommendationService(
        quantity=100
    )

    with pytest.raises(
        ValueError,
        match="No supplier can satisfy",
    ):
        service.recommend(
            [mouser, arrow]
        )


def test_recommendation_excludes_ineligible_suppliers():
    eligible = make_quote(
        supplier="mouser",
        unit_price=1.20,
        quantity_available=5000,
        moq=10,
    )

    ineligible = make_quote(
        supplier="arrow",
        unit_price=0.50,
        quantity_available=5000,
        moq=500,
    )

    service = ProcurementRecommendationService(
        quantity=100
    )

    result = service.recommend(
        [eligible, ineligible]
    )

    assert result.action == "BUY"
    assert result.supplier == "mouser"

    assert all(
        alternative.supplier != "arrow"
        for alternative in result.alternatives
    )


def test_recommendation_is_deterministic():
    arrow = make_quote(
        supplier="arrow",
        unit_price=1.00,
        quantity_available=5000,
    )

    mouser = make_quote(
        supplier="mouser",
        unit_price=1.00,
        quantity_available=5000,
    )

    service = ProcurementRecommendationService(
        quantity=100
    )

    first = service.recommend(
        [arrow, mouser]
    )

    second = service.recommend(
        [arrow, mouser]
    )

    assert first.action == second.action
    assert first.supplier == second.supplier
    assert first.score == second.score