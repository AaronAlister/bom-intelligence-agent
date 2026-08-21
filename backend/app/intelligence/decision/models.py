from dataclasses import dataclass
from enum import StrEnum


class DecisionAction(StrEnum):
    """Recommended procurement action."""

    BUY = "BUY"
    REVIEW = "REVIEW"
    REPLACE = "REPLACE"
    SOURCE_ALTERNATIVE = "SOURCE_ALTERNATIVE"


@dataclass(slots=True, frozen=True)
class DecisionFactor:
    """Explainable factor contributing to a decision."""

    name: str
    value: str
    impact: str


@dataclass(slots=True, frozen=True)
class ComponentDecision:
    """Final procurement decision for one component."""

    mpn: str
    manufacturer: str | None

    action: DecisionAction

    supplier: str | None
    supplier_score: float | None

    risk_score: float | None
    lifecycle_status: str | None
    availability: int | None

    estimated_unit_price: float | None
    estimated_total_cost: float | None
    currency: str | None

    factors: list[DecisionFactor]

    reason: str