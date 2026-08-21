from dataclasses import dataclass
from enum import StrEnum


class RiskSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class ComponentRiskAssessment:
    """
    Explainable risk assessment for a component.
    """

    score: float
    severity: RiskSeverity

    lifecycle_score: float
    availability_score: float

    reasons: list[str]