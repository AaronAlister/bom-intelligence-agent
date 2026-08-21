from dataclasses import dataclass

from backend.app.intelligence.availability.procurement import (
    ComponentProcurementResult,
)
from backend.app.intelligence.decision.models import (
    ComponentDecision,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
)
from backend.app.intelligence.risk.models import (
    ComponentRiskAssessment,
)


@dataclass(slots=True)
class ComponentIntelligenceResult:
    """
    Unified intelligence result for a single component.
    """

    mpn: str
    manufacturer: str | None

    procurement: ComponentProcurementResult

    lifecycle: LifecycleAssessment

    risk: ComponentRiskAssessment | None = None

    decision: ComponentDecision | None = None