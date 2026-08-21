from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


class DistributorEnrichmentService:
    """
    Queries all configured distributor providers.

    Unlike EnrichmentOrchestrator, this service does not stop
    after the first successful provider. It collects every
    successful enrichment result so downstream services can
    perform procurement and availability analysis.
    """

    def __init__(
        self,
        providers: list[ComponentEnrichmentProvider],
    ) -> None:
        if not providers:
            raise ValueError(
                "At least one enrichment provider is required"
            )

        self._providers = providers

    async def enrich_all(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> list[ComponentEnrichmentResult]:
        """
        Query every provider and return successful results.

        Provider failures and NOT_FOUND responses are ignored
        so one distributor cannot prevent other distributors
        from being queried.
        """

        results: list[ComponentEnrichmentResult] = []

        for provider in self._providers:
            try:
                result = await provider.enrich(
                    mpn=mpn,
                    manufacturer=manufacturer,
                )

            except Exception:
                # A distributor failure must not prevent the
                # remaining distributors from being queried.
                continue

            if result is None:
                continue

            results.append(result)

        return results

    @property
    def providers(
        self,
    ) -> tuple[ComponentEnrichmentProvider, ...]:
        """Return providers in configured order."""

        return tuple(self._providers)