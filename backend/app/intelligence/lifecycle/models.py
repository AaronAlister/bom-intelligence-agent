from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class LifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    NRND = "NRND"
    EOL = "EOL"
    OBSOLETE = "OBSOLETE"
    UNKNOWN = "UNKNOWN"


class LifecycleRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class LifecycleAssessment:
    """
    Current lifecycle assessment for a component.
    """

    status: LifecycleStatus

    eol_date: date | None
    last_buy_date: date | None

    risk: LifecycleRisk

    source: str | None