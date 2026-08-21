import pytest

from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.enrichment.registry import (
    EnrichmentProviderRegistry,
)


class MockProvider(ComponentEnrichmentProvider):
    @property
    def name(self) -> str:
        return "mock"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        return ComponentEnrichmentResult(
            mpn=mpn,
            manufacturer=manufacturer,
            source=self.name,
        )


def test_register_and_get_provider():
    registry = EnrichmentProviderRegistry()

    provider = MockProvider()

    registry.register(provider)

    assert registry.get("mock") is provider
    assert registry.list_names() == ["mock"]


def test_provider_names_are_case_insensitive():
    registry = EnrichmentProviderRegistry()

    provider = MockProvider()

    registry.register(provider)

    assert registry.get("MOCK") is provider
    assert registry.get(" Mock ") is provider


def test_duplicate_provider_is_rejected():
    registry = EnrichmentProviderRegistry()

    registry.register(MockProvider())

    with pytest.raises(ValueError):
        registry.register(MockProvider())


def test_unknown_provider_is_rejected():
    registry = EnrichmentProviderRegistry()

    with pytest.raises(KeyError):
        registry.get("does-not-exist")