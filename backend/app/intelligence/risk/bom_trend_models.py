from dataclasses import dataclass

from backend.app.intelligence.risk.models import RiskSeverity


class RiskTrend:
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    WORSENING = "WORSENING"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class BOMRiskTrend:
    """
    Historical trend of BOM risk.
    """

    trend: str

    snapshot_count: int

    previous_score: float | None
    current_score: float | None
    score_change: float | None

    previous_severity: RiskSeverity
    current_severity: RiskSeverity

    previous_high_risk_count: int | None
    current_high_risk_count: int | None
    high_risk_count_change: int | None

    previous_critical_count: int | None
    current_critical_count: int | None
    critical_count_change: int | None

    previous_lifecycle_risk_count: int | None
    current_lifecycle_risk_count: int | None
    lifecycle_risk_count_change: int | None

    previous_availability_risk_count: int | None
    current_availability_risk_count: int | None
    availability_risk_count_change: int | None