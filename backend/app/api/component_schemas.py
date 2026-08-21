from datetime import datetime

from pydantic import BaseModel, ConfigDict


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

    compatibility_status: str   # <-- NEW FIELD

    category_match: bool
    package_match: bool
    manufacturer_match: bool

    lifecycle_score: float
    availability_score: float

    reasons: list[str]


class AlternativeResponse(BaseModel):
    """Complete alternative-component analysis."""

    model_config = ConfigDict(from_attributes=True)

    source_mpn: str

    candidates: list[AlternativeCandidateResponse]

    best_candidate: AlternativeCandidateResponse | None


class AlternativePersistResponse(BaseModel):
    """Result of persisted alternative analysis."""

    model_config = ConfigDict(from_attributes=True)

    source_mpn: str

    candidates: list[AlternativeCandidateResponse]

    best_candidate: AlternativeCandidateResponse | None

    persisted_count: int


class AlternativeHistoryResponse(BaseModel):
    """Persisted alternative recommendation record."""

    model_config = ConfigDict(from_attributes=True)

    id: int

    source_component_id: int
    alternative_component_id: int

    compatibility_score: float

    category_match: bool
    package_match: bool
    manufacturer_match: bool

    lifecycle_score: float
    availability_score: float

    reasons: list[str]

    created_at: datetime


class AlternativeHistoryListResponse(BaseModel):
    """Historical alternative recommendations."""

    model_config = ConfigDict(from_attributes=True)

    source_component_id: int

    records: list[AlternativeHistoryResponse]


class ComponentResponse(BaseModel):
    """Component information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    mpn: str
    manufacturer: str | None
    description: str | None
    category: str | None
    package: str | None

    normalized_mpn: str | None
    normalized_manufacturer: str | None
    normalized_category: str | None

    datasheet_url: str | None
    manufacturer_part_url: str | None

    enrichment_status: str
    enriched_at: datetime | None
    created_at: datetime


class ComponentListResponse(BaseModel):
    """Paginated list of components in the workspace."""

    components: list[ComponentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ComponentEnrichmentResponse(BaseModel):
    """Result of component enrichment."""

    component: ComponentResponse
    status: str