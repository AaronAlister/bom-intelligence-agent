from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportComponentRisk(BaseModel):
    """Risk summary for one component in a BOM."""

    model_config = ConfigDict(from_attributes=True)

    component_id: int
    mpn: str
    manufacturer: str | None
    quantity: int

    score: float
    severity: str

    lifecycle_risk: bool
    availability_risk: bool


class ReportRiskDriver(BaseModel):
    """Explainable risk driver included in the report."""

    model_config = ConfigDict(from_attributes=True)

    component_id: int
    mpn: str
    score: float
    severity: str
    reason: str


class ReportRecommendation(BaseModel):
    """Recommended action included in the report."""

    model_config = ConfigDict(from_attributes=True)

    priority: str
    component_id: int | None
    mpn: str | None
    action: str
    reason: str


class ReportLifecycleSummary(BaseModel):
    """Lifecycle summary for the BOM."""

    active_count: int
    nrnd_count: int
    eol_count: int
    obsolete_count: int
    unknown_count: int

    lifecycle_risk_count: int


class ReportAvailabilitySummary(BaseModel):
    """Availability summary for the BOM."""

    availability_risk_count: int
    components_with_availability: int
    components_without_availability: int


class BOMReport(BaseModel):
    """Complete report data for a BOM."""

    model_config = ConfigDict(from_attributes=True)

    bom_id: int

    generated_at: datetime

    product: str | None
    revision: str | None
    source_file: str | None
    source_format: str | None

    component_count: int
    total_quantity: int

    overall_score: float
    severity: str

    high_risk_count: int
    critical_count: int
    lifecycle_risk_count: int
    availability_risk_count: int

    summary: str

    lifecycle: ReportLifecycleSummary
    availability: ReportAvailabilitySummary

    top_risk_components: list[ReportComponentRisk]

    risk_drivers: list[ReportRiskDriver]

    recommendations: list[ReportRecommendation]