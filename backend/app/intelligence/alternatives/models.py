from dataclasses import dataclass

from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


@dataclass(slots=True)
class AlternativeCandidate:
    """
    Candidate component that may replace a source component.
    """

    component: ComponentEnrichmentResult

    compatibility_score: float

    category_match: bool
    package_match: bool
    manufacturer_match: bool

    lifecycle_score: float
    availability_score: float

    reasons: list[str]

    compatibility_status: str = "REVIEW"


@dataclass(slots=True)
class AlternativeAnalysis:
    """
    Ranked alternatives for a component.
    """

    source_mpn: str

    candidates: list[AlternativeCandidate]

    best_candidate: AlternativeCandidate | None