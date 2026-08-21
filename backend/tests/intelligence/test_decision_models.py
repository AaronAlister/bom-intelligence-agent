import pytest

from backend.app.intelligence.decision.models import (
    ComponentDecision,
    DecisionAction,
    DecisionFactor,
)


def test_decision_action_values():
    assert DecisionAction.BUY == "BUY"
    assert DecisionAction.REVIEW == "REVIEW"
    assert DecisionAction.REPLACE == "REPLACE"
    assert (
        DecisionAction.SOURCE_ALTERNATIVE
        == "SOURCE_ALTERNATIVE"
    )


def test_component_decision_model():
    decision = ComponentDecision(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        action=DecisionAction.BUY,
        supplier="digikey",
        supplier_score=91.5,
        risk_score=12.0,
        lifecycle_status="Active",
        availability=8100,
        estimated_unit_price=1.60,
        estimated_total_cost=160.00,
        currency="USD",
        factors=[
            DecisionFactor(
                name="availability",
                value="8100",
                impact="positive",
            )
        ],
        reason="Component is suitable for procurement.",
    )

    assert decision.mpn == "LM358DR"
    assert decision.action == DecisionAction.BUY
    assert decision.supplier == "digikey"
    assert decision.estimated_total_cost == 160.00
    assert len(decision.factors) == 1


def test_decision_factor_is_immutable():
    factor = DecisionFactor(
        name="risk",
        value="12",
        impact="positive",
    )

    with pytest.raises(AttributeError):
        factor.name = "availability"  # type: ignore[reportAttributeAccessIssue]