from dataclasses import dataclass

from backend.app.intelligence.risk.models import RiskSeverity


@dataclass(slots=True)
class BOMComponentRisk:
    """
    Risk information for one component within a BOM.
    """

    component_id: int
    mpn: str
    quantity: int

    score: float
    severity: RiskSeverity

    lifecycle_risk: bool = False
    availability_risk: bool = False


@dataclass(slots=True)
class BOMRiskAssessment:
    """
    Aggregated risk assessment for an entire BOM.
    """

    overall_score: float
    severity: RiskSeverity

    component_count: int
    high_risk_count: int
    critical_count: int

    lifecycle_risk_count: int
    availability_risk_count: int

    top_risk_components: list[BOMComponentRisk]