from dataclasses import dataclass

from backend.app.intelligence.availability.models import (
    AvailabilitySummary,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


@dataclass(slots=True)
class ComponentProcurementResult:
    """
    Unified procurement intelligence for a component.
    """

    mpn: str
    manufacturer: str | None

    distributor_results: list[
        ComponentEnrichmentResult
    ]

    availability: AvailabilitySummary