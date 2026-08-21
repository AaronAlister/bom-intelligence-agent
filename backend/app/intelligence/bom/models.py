from dataclasses import dataclass

from backend.app.intelligence.availability.supplier.bom_cost import (
    BOMCost,
)
from backend.app.intelligence.risk.bom_models import (
    BOMRiskAssessment,
)
from backend.app.intelligence.risk.bom_explainer import (
    BOMRiskExplanation,
)
from backend.app.intelligence.component.models import (
    ComponentIntelligenceResult,
)


@dataclass(slots=True)
class BOMComponentIntelligence:
    """Intelligence result for one component in a BOM."""

    component_id: int
    mpn: str
    quantity: int

    intelligence: ComponentIntelligenceResult


@dataclass(slots=True)
class BOMIntelligenceResult:
    """Unified intelligence result for an entire BOM."""

    components: list[BOMComponentIntelligence]

    cost: BOMCost
    risk: BOMRiskAssessment
    risk_explanation: BOMRiskExplanation