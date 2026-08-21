from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.intelligence.risk.models import RiskSeverity


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
    """Explanation of a BOM risk driver."""

    model_config = ConfigDict(from_attributes=True)

    component_id: int
    mpn: str
    score: float
    severity: RiskSeverity
    reason: str


class BOMRiskRecommendationResponse(BaseModel):
    """Recommended action for a BOM risk."""

    model_config = ConfigDict(from_attributes=True)

    priority: RiskSeverity
    component_id: int | None
    mpn: str | None
    action: str
    reason: str


class BOMRiskResponse(BaseModel):
    """Complete BOM risk intelligence response."""

    model_config = ConfigDict(from_attributes=True)

    bom_id: int

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

    summary: str

    risk_drivers: list[
        BOMRiskDriverResponse
    ]

    recommendations: list[
        BOMRiskRecommendationResponse
    ]


class BOMRiskHistorySnapshotResponse(BaseModel):
    """Historical BOM risk snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    overall_score: float
    severity: RiskSeverity

    component_count: int
    high_risk_count: int
    critical_count: int

    lifecycle_risk_count: int
    availability_risk_count: int

    created_at: datetime


class BOMRiskTrendResponse(BaseModel):
    """Calculated BOM risk trend."""

    model_config = ConfigDict(from_attributes=True)

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


class BOMRiskHistoryResponse(BaseModel):
    """Complete BOM risk history and trend."""

    model_config = ConfigDict(from_attributes=True)

    bom_id: int

    snapshot_count: int

    trend: BOMRiskTrendResponse

    history: list[BOMRiskHistorySnapshotResponse]


class AlternativeComponentResponse(BaseModel):
    """Alternative component candidate."""

    model_config = ConfigDict(from_attributes=True)

    mpn: str
    manufacturer: str | None
    description: str | None
    category: str | None
    package: str | None


class AlternativeCandidateResponse(BaseModel):
    """Ranked alternative component."""

    model_config = ConfigDict(from_attributes=True)

    component: AlternativeComponentResponse

    compatibility_score: float

    category_match: bool
    package_match: bool
    manufacturer_match: bool

    lifecycle_score: float
    availability_score: float

    reasons: list[str]


class AlternativeResponse(BaseModel):
    """Complete alternative-component analysis."""

    source_mpn: str

    candidates: list[
        AlternativeCandidateResponse
    ]

    best_candidate: (
        AlternativeCandidateResponse | None
    )
