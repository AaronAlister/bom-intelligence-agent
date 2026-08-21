from backend.app.intelligence.risk.bom_assessor import (
    BOMRiskAssessor,
)
from backend.app.intelligence.risk.bom_models import (
    BOMComponentRisk,
)
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)


def test_empty_bom_has_unknown_risk():
    result = BOMRiskAssessor.assess([])

    assert result.overall_score == 0.0
    assert result.severity == RiskSeverity.UNKNOWN

    assert result.component_count == 0
    assert result.high_risk_count == 0
    assert result.critical_count == 0

    assert result.top_risk_components == []


def test_low_risk_bom():
    risks = [
        BOMComponentRisk(
            component_id=1,
            mpn="COMP-A",
            quantity=10,
            score=0.0,
            severity=RiskSeverity.LOW,
        ),
        BOMComponentRisk(
            component_id=2,
            mpn="COMP-B",
            quantity=5,
            score=10.0,
            severity=RiskSeverity.LOW,
        ),
    ]

    result = BOMRiskAssessor.assess(risks)

    assert result.overall_score == 5.0
    assert result.severity == RiskSeverity.LOW

    assert result.component_count == 2
    assert result.high_risk_count == 0
    assert result.critical_count == 0


def test_bom_detects_high_and_critical_components():
    risks = [
        BOMComponentRisk(
            component_id=1,
            mpn="LOW-PART",
            quantity=10,
            score=10.0,
            severity=RiskSeverity.LOW,
        ),
        BOMComponentRisk(
            component_id=2,
            mpn="HIGH-PART",
            quantity=2,
            score=70.0,
            severity=RiskSeverity.HIGH,
            lifecycle_risk=True,
        ),
        BOMComponentRisk(
            component_id=3,
            mpn="CRITICAL-PART",
            quantity=1,
            score=95.0,
            severity=RiskSeverity.CRITICAL,
            lifecycle_risk=True,
            availability_risk=True,
        ),
    ]

    result = BOMRiskAssessor.assess(risks)

    assert result.overall_score == 58.33
    assert result.severity == RiskSeverity.HIGH

    assert result.component_count == 3
    assert result.high_risk_count == 2
    assert result.critical_count == 1

    assert result.lifecycle_risk_count == 2
    assert result.availability_risk_count == 1


def test_top_risk_components_are_sorted():
    risks = [
        BOMComponentRisk(
            component_id=1,
            mpn="LOW",
            quantity=1,
            score=5.0,
            severity=RiskSeverity.LOW,
        ),
        BOMComponentRisk(
            component_id=2,
            mpn="CRITICAL",
            quantity=1,
            score=95.0,
            severity=RiskSeverity.CRITICAL,
        ),
        BOMComponentRisk(
            component_id=3,
            mpn="MEDIUM",
            quantity=1,
            score=40.0,
            severity=RiskSeverity.MEDIUM,
        ),
    ]

    result = BOMRiskAssessor.assess(risks)

    assert (
        result.top_risk_components[0].mpn
        == "CRITICAL"
    )

    assert (
        result.top_risk_components[1].mpn
        == "MEDIUM"
    )

    assert (
        result.top_risk_components[2].mpn
        == "LOW"
    )