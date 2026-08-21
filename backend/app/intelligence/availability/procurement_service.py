from backend.app.intelligence.availability.aggregator import (
    AvailabilityAggregator,
)
from backend.app.intelligence.availability.procurement import (
    ComponentProcurementResult,
)
from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.distributor_service import (
    DistributorEnrichmentService,
)


class ComponentProcurementService:
    """
    Coordinates multi-distributor enrichment and availability
    aggregation for a single component.
    """

    def __init__(
        self,
        providers: list[ComponentEnrichmentProvider],
    ) -> None:
        self._distributor_service = (
            DistributorEnrichmentService(
                providers
            )
        )

    async def analyze(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentProcurementResult:
        """
        Enrich a component across all distributors and
        aggregate its procurement availability.
        """

        results = (
            await self._distributor_service.enrich_all(
                mpn=mpn,
                manufacturer=manufacturer,
            )
        )

        availability = (
            AvailabilityAggregator.from_results(
                results
            )
        )

        return ComponentProcurementResult(
            mpn=mpn,
            manufacturer=manufacturer,
            distributor_results=results,
            availability=availability,
        )

    @property
    def providers(
        self,
    ) -> tuple[ComponentEnrichmentProvider, ...]:
        """Return configured distributor providers."""

        return self._distributor_service.providers