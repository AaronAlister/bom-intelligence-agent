from datetime import date

from pydantic import BaseModel, ConfigDict

from backend.app.intelligence.availability.models import (
    AvailabilityStatus,
    ProcurementStatus,
)
from backend.app.intelligence.decision.models import (
    DecisionAction,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleRisk,
    LifecycleStatus,
)
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)


class DistributorIntelligenceResponse(BaseModel):
    """Normalized distributor intelligence."""

    model_config = ConfigDict(from_attributes=True)

    mpn: str | None
    manufacturer: str | None
    description: str | None
    category: str | None
    package: str | None
    datasheet_url: str | None
    manufacturer_part_url: str | None
    availability: int | None
    lifecycle_status: str | None
    source: str


class DistributorAvailabilityResponse(BaseModel):
    """Availability from a single distributor."""

    model_config = ConfigDict(from_attributes=True)

    distributor: str
    quantity_available: int | None
    status: AvailabilityStatus


class AvailabilityResponse(BaseModel):
    """Aggregated distributor availability."""

    model_config = ConfigDict(from_attributes=True)

    distributors: list[
        DistributorAvailabilityResponse
    ]

    total_distributor_quantity: int
    distributors_available: int
    distributors_unavailable: int

    best_available_quantity: int | None
    procurement_status: ProcurementStatus


class ProcurementResponse(BaseModel):
    """Component procurement intelligence."""

    model_config = ConfigDict(from_attributes=True)

    mpn: str
    manufacturer: str | None

    distributor_results: list[
        DistributorIntelligenceResponse
    ]

    availability: AvailabilityResponse


class LifecycleResponse(BaseModel):
    """Component lifecycle assessment."""

    model_config = ConfigDict(from_attributes=True)

    status: LifecycleStatus
    eol_date: date | None
    last_buy_date: date | None

    risk: LifecycleRisk
    source: str | None


class RiskResponse(BaseModel):
    """Explainable component risk."""

    model_config = ConfigDict(from_attributes=True)

    score: float
    severity: RiskSeverity

    lifecycle_score: float
    availability_score: float

    reasons: list[str]


class DecisionFactorResponse(BaseModel):
    """Explainable decision factor."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    value: str
    impact: str


class DecisionResponse(BaseModel):
    """Final procurement decision."""

    model_config = ConfigDict(from_attributes=True)

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

    factors: list[DecisionFactorResponse]

    reason: str


class ComponentIntelligenceResponse(BaseModel):
    """Complete public component intelligence response."""

    model_config = ConfigDict(from_attributes=True)

    mpn: str
    manufacturer: str | None

    procurement: ProcurementResponse
    lifecycle: LifecycleResponse
    risk: RiskResponse | None
    decision: DecisionResponse | None

class BOMComponentCostResponse(BaseModel):
    """Cost breakdown for one BOM component."""

    model_config = ConfigDict(from_attributes=True)

    supplier: str
    mpn: str
    quantity: int

    unit_price: float | None
    total_cost: float | None
    currency: str | None


class BOMCostResponse(BaseModel):
    """Aggregated BOM procurement cost."""

    model_config = ConfigDict(from_attributes=True)

    components: list[BOMComponentCostResponse]

    total_cost: float | None
    currency: str | None


class BOMRiskComponentResponse(BaseModel):
    """Risk information for one BOM component."""

    model_config = ConfigDict(from_attributes=True)

    component_id: int
    mpn: str
    quantity: int

    score: float
    severity: RiskSeverity

    lifecycle_risk: bool
    availability_risk: bool


class BOMRiskDriverResponse(BaseModel):
    """Major source of BOM risk."""

    model_config = ConfigDict(from_attributes=True)

    component_id: int
    mpn: str
    score: float
    severity: RiskSeverity
    reason: str


class BOMRiskRecommendationResponse(BaseModel):
    """BOM-level procurement recommendation."""

    model_config = ConfigDict(from_attributes=True)

    priority: RiskSeverity

    component_id: int | None
    mpn: str | None

    action: str
    reason: str


class BOMRiskResponse(BaseModel):
    """Aggregated BOM risk intelligence."""

    model_config = ConfigDict(from_attributes=True)

    overall_score: float
    severity: RiskSeverity

    component_count: int
    high_risk_count: int
    critical_count: int

    lifecycle_risk_count: int
    availability_risk_count: int

    top_risk_components: list[
        BOMRiskComponentResponse
    ]


class BOMRiskExplanationResponse(BaseModel):
    """Explainable BOM risk intelligence."""

    model_config = ConfigDict(from_attributes=True)

    summary: str

    risk_drivers: list[
        BOMRiskDriverResponse
    ]

    recommendations: list[
        BOMRiskRecommendationResponse
    ]


class BOMComponentIntelligenceResponse(BaseModel):
    """Intelligence for one component within a BOM."""

    model_config = ConfigDict(from_attributes=True)

    component_id: int
    mpn: str
    quantity: int

    intelligence: ComponentIntelligenceResponse


class BOMIntelligenceResponse(BaseModel):
    """Complete BOM intelligence response."""

    model_config = ConfigDict(from_attributes=True)

    components: list[
        BOMComponentIntelligenceResponse
    ]

    cost: BOMCostResponse

    risk: BOMRiskResponse

    risk_explanation: BOMRiskExplanationResponse