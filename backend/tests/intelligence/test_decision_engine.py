import pytest

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.decision.engine import (
    ComponentDecisionEngine,
)
from backend.app.intelligence.decision.models import (
    DecisionAction,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
    LifecycleRisk,
    LifecycleStatus,
)
from backend.app.intelligence.risk.models import (
    ComponentRiskAssessment,
    RiskSeverity,
)


def make_quote(
    supplier: str,
    price: float,
    quantity_available: int = 5000,
) -> SupplierQuote:
    return SupplierQuote(
        supplier=supplier,
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=price,
        currency="USD",
        quantity_available=quantity_available,
        source=supplier,
    )


def make_low_risk() -> ComponentRiskAssessment:
    return ComponentRiskAssessment(
        score=15.0,
        severity=RiskSeverity.LOW,
        lifecycle_score=5.0,
        availability_score=10.0,
        reasons=["Component is readily available."],
    )


def make_active_lifecycle() -> LifecycleAssessment:
    return LifecycleAssessment(
        status=LifecycleStatus.ACTIVE,
        eol_date=None,
        last_buy_date=None,
        risk=LifecycleRisk.LOW,
        source="test",
    )


def test_engine_selects_best_supplier():
    engine = ComponentDecisionEngine(
        quantity=100
    )

    result = engine.decide(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quotes=[
            make_quote("mouser", 2.40),
            make_quote("arrow", 1.85),
            make_quote("digikey", 1.60),
        ],
        risk=make_low_risk(),
        lifecycle=make_active_lifecycle(),
    )

    assert result.mpn == "LM358DR"
    assert result.action == DecisionAction.BUY
    assert result.supplier == "digikey"
    assert result.estimated_unit_price == 1.60
    assert result.estimated_total_cost == 160.00
    assert result.currency == "USD"


def test_engine_includes_risk_and_lifecycle_information():
    engine = ComponentDecisionEngine(
        quantity=100
    )

    result = engine.decide(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quotes=[
            make_quote("digikey", 1.60),
        ],
        risk=make_low_risk(),
        lifecycle=make_active_lifecycle(),
    )

    assert result.risk_score == 15.0
    assert result.lifecycle_status == "ACTIVE"

    assert any(
        factor.name == "risk"
        for factor in result.factors
    )

    assert any(
        factor.name == "lifecycle"
        for factor in result.factors
    )


def test_engine_returns_review_for_high_risk():
    engine = ComponentDecisionEngine(
        quantity=100
    )

    risk = ComponentRiskAssessment(
        score=85.0,
        severity=RiskSeverity.HIGH,
        lifecycle_score=40.0,
        availability_score=45.0,
        reasons=["High component risk."],
    )

    result = engine.decide(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quotes=[
            make_quote("digikey", 1.60),
        ],
        risk=risk,
        lifecycle=make_active_lifecycle(),
    )

    assert result.action == DecisionAction.REVIEW
    assert result.supplier == "digikey"
    assert result.risk_score == 85.0


def test_engine_returns_review_for_high_lifecycle_risk():
    engine = ComponentDecisionEngine(
        quantity=100
    )

    lifecycle = LifecycleAssessment(
        status=LifecycleStatus.EOL,
        eol_date=None,
        last_buy_date=None,
        risk=LifecycleRisk.HIGH,
        source="test",
    )

    result = engine.decide(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quotes=[
            make_quote("digikey", 1.60),
        ],
        risk=make_low_risk(),
        lifecycle=lifecycle,
    )

    assert result.action == DecisionAction.REVIEW
    assert result.lifecycle_status == "EOL"


def test_engine_sources_alternative_when_no_supplier_can_fulfill():
    engine = ComponentDecisionEngine(
        quantity=1000
    )

    result = engine.decide(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quotes=[
            make_quote(
                "mouser",
                2.40,
                quantity_available=50,
            ),
        ],
        risk=make_low_risk(),
        lifecycle=make_active_lifecycle(),
    )

    assert (
        result.action
        == DecisionAction.SOURCE_ALTERNATIVE
    )

    assert result.supplier is None
    assert result.estimated_total_cost is None


def test_engine_handles_no_quotes():
    engine = ComponentDecisionEngine(
        quantity=100
    )

    result = engine.decide(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quotes=[],
    )

    assert (
        result.action
        == DecisionAction.SOURCE_ALTERNATIVE
    )

    assert result.supplier is None
    assert result.risk_score is None
    assert result.lifecycle_status is None


def test_engine_rejects_invalid_quantity():
    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        ComponentDecisionEngine(
            quantity=0
        )