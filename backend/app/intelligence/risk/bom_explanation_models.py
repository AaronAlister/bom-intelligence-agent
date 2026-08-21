from dataclasses import dataclass

from backend.app.intelligence.risk.models import RiskSeverity


@dataclass(slots=True)
class BOMRiskDriver:
    """
    Explains one major source of BOM risk.
    """

    component_id: int
    mpn: str
    score: float
    severity: RiskSeverity
    reason: str


@dataclass(slots=True)
class BOMRiskRecommendation:
    """
    Actionable recommendation derived from BOM risk.
    """

    priority: RiskSeverity
    component_id: int | None
    mpn: str | None
    action: str
    reason: str


@dataclass(slots=True)
class BOMRiskExplanation:
    """
    Human-readable explanation of a BOM risk assessment.
    """

    summary: str
    risk_drivers: list[BOMRiskDriver]
    recommendations: list[BOMRiskRecommendation]