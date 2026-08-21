from backend.app.intelligence.risk.bom_explainer import (
    BOMRiskExplainer,
)
from backend.app.intelligence.risk.bom_models import (
    BOMComponentRisk,
    BOMRiskAssessment,
)
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)


def test_explainer_handles_empty_bom():
    assessment = BOMRiskAssessment(
        overall_score=0.0,
        severity=RiskSeverity.UNKNOWN,
        component_count=0,
        high_risk_count=0,
        critical_count=0,
        lifecycle_risk_count=0,
        availability_risk_count=0,
        top_risk_components=[],
    )

    result = BOMRiskExplainer.explain(
        assessment
    )

    assert (
        result.summary
        == "No component risk data is available "
        "for this BOM."
    )

    assert result.risk_drivers == []
    assert len(result.recommendations) == 1

    assert (
        result.recommendations[0].priority
        == RiskSeverity.UNKNOWN
    )


def test_explainer_identifies_risk_drivers():
    assessment = BOMRiskAssessment(
        overall_score=72.5,
        severity=RiskSeverity.HIGH,
        component_count=3,
        high_risk_count=2,
        critical_count=1,
        lifecycle_risk_count=2,
        availability_risk_count=1,
        top_risk_components=[
            BOMComponentRisk(
                component_id=3,
                mpn="CRITICAL-PART",
                quantity=1,
                score=95.0,
                severity=RiskSeverity.CRITICAL,
                lifecycle_risk=True,
                availability_risk=True,
            ),
            BOMComponentRisk(
                component_id=2,
                mpn="HIGH-PART",
                quantity=2,
                score=70.0,
                severity=RiskSeverity.HIGH,
                lifecycle_risk=True,
                availability_risk=False,
            ),
            BOMComponentRisk(
                component_id=1,
                mpn="LOW-PART",
                quantity=10,
                score=10.0,
                severity=RiskSeverity.LOW,
            ),
        ],
    )

    result = BOMRiskExplainer.explain(
        assessment
    )

    assert (
        "HIGH"
        in result.summary
    )

    assert len(result.risk_drivers) == 2

    assert (
        result.risk_drivers[0].mpn
        == "CRITICAL-PART"
    )

    assert (
        result.risk_drivers[0].reason
        == "Component has both lifecycle and "
        "availability risk."
    )

    assert (
        result.risk_drivers[1].mpn
        == "HIGH-PART"
    )

    assert (
        result.risk_drivers[1].reason
        == "Component has elevated lifecycle risk."
    )


def test_explainer_generates_critical_recommendation():
    assessment = BOMRiskAssessment(
        overall_score=95.0,
        severity=RiskSeverity.CRITICAL,
        component_count=1,
        high_risk_count=1,
        critical_count=1,
        lifecycle_risk_count=1,
        availability_risk_count=1,
        top_risk_components=[
            BOMComponentRisk(
                component_id=99,
                mpn="CRITICAL-MPN",
                quantity=1,
                score=95.0,
                severity=RiskSeverity.CRITICAL,
                lifecycle_risk=True,
                availability_risk=True,
            ),
        ],
    )

    result = BOMRiskExplainer.explain(
        assessment
    )

    component_recommendations = [
        recommendation
        for recommendation in result.recommendations
        if recommendation.component_id == 99
    ]

    assert len(component_recommendations) == 1

    recommendation = (
        component_recommendations[0]
    )

    assert (
        recommendation.priority
        == RiskSeverity.CRITICAL
    )

    assert (
        "alternate-component"
        in recommendation.action
    )


def test_explainer_generates_lifecycle_and_availability_actions():
    assessment = BOMRiskAssessment(
        overall_score=60.0,
        severity=RiskSeverity.HIGH,
        component_count=2,
        high_risk_count=2,
        critical_count=0,
        lifecycle_risk_count=1,
        availability_risk_count=1,
        top_risk_components=[
            BOMComponentRisk(
                component_id=1,
                mpn="LIFECYCLE-PART",
                quantity=1,
                score=65.0,
                severity=RiskSeverity.HIGH,
                lifecycle_risk=True,
            ),
            BOMComponentRisk(
                component_id=2,
                mpn="AVAILABILITY-PART",
                quantity=1,
                score=55.0,
                severity=RiskSeverity.HIGH,
                availability_risk=True,
            ),
        ],
    )

    result = BOMRiskExplainer.explain(
        assessment
    )

    component_actions = [
        recommendation
        for recommendation in result.recommendations
        if recommendation.component_id is not None
    ]

    assert len(component_actions) == 2

    assert any(
        "lifecycle"
        in recommendation.action.lower()
        for recommendation in component_actions
    )

    assert any(
        "availability"
        in recommendation.action.lower()
        or "supplier"
        in recommendation.action.lower()
        for recommendation in component_actions
    )

    assert any(
        recommendation.component_id is None
        for recommendation in result.recommendations
    )