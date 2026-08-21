from abc import ABC, abstractmethod

from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


class ComponentEnrichmentProvider(ABC):
    """Interface implemented by component enrichment providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        raise NotImplementedError

    @abstractmethod
    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        """
        Enrich a component.

        Returns None when the provider cannot find the component.
        """
        raise NotImplementedError