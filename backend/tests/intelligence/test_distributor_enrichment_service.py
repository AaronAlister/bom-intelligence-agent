import pytest

from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.distributor_service import (
    DistributorEnrichmentService,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


class MockProvider(
    ComponentEnrichmentProvider,
):
    def __init__(
        self,
        provider_name: str,
        result: ComponentEnrichmentResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._name = provider_name
        self._result = result
        self._error = error
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        self.calls += 1

        if self._error is not None:
            raise self._error

        return self._result


@pytest.mark.asyncio
async def test_enrich_all_queries_every_provider():
    mouser = MockProvider(
        "mouser",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=5000,
            source="mouser",
        ),
    )

    arrow = MockProvider(
        "arrow",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=4200,
            source="arrow",
        ),
    )

    digikey = MockProvider(
        "digikey",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=8100,
            source="digikey",
        ),
    )

    service = DistributorEnrichmentService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    results = await service.enrich_all(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert len(results) == 3

    assert [result.source for result in results] == [
        "mouser",
        "arrow",
        "digikey",
    ]

    assert [result.availability for result in results] == [
        5000,
        4200,
        8100,
    ]

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_enrich_all_ignores_not_found_results():
    mouser = MockProvider(
        "mouser",
        None,
    )

    arrow = MockProvider(
        "arrow",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=4200,
            source="arrow",
        ),
    )

    digikey = MockProvider(
        "digikey",
        None,
    )

    service = DistributorEnrichmentService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    results = await service.enrich_all(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert len(results) == 1

    assert results[0].source == "arrow"
    assert results[0].availability == 4200

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_enrich_all_continues_after_provider_failure():
    mouser = MockProvider(
        "mouser",
        error=RuntimeError("Mouser unavailable"),
    )

    arrow = MockProvider(
        "arrow",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=4200,
            source="arrow",
        ),
    )

    digikey = MockProvider(
        "digikey",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=8100,
            source="digikey",
        ),
    )

    service = DistributorEnrichmentService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    results = await service.enrich_all(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert len(results) == 2

    assert [result.source for result in results] == [
        "arrow",
        "digikey",
    ]

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_enrich_all_returns_empty_when_no_provider_succeeds():
    mouser = MockProvider(
        "mouser",
        None,
    )

    arrow = MockProvider(
        "arrow",
        error=RuntimeError("Arrow unavailable"),
    )

    digikey = MockProvider(
        "digikey",
        None,
    )

    service = DistributorEnrichmentService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    results = await service.enrich_all(
        mpn="UNKNOWN",
        manufacturer="Unknown",
    )

    assert results == []

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


def test_service_requires_at_least_one_provider():
    with pytest.raises(
        ValueError,
        match="At least one enrichment provider",
    ):
        DistributorEnrichmentService([])