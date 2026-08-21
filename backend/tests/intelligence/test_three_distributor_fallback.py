import pytest

from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.enrichment.orchestrator import (
    EnrichmentOrchestrator,
)


class MockDistributor(
    ComponentEnrichmentProvider,
):
    def __init__(
        self,
        provider_name: str,
        result: ComponentEnrichmentResult | None,
    ) -> None:
        self._name = provider_name
        self._result = result
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
        return self._result


@pytest.mark.asyncio
async def test_three_level_fallback_reaches_digikey():
    mouser = MockDistributor(
        "mouser",
        None,
    )

    arrow = MockDistributor(
        "arrow",
        None,
    )

    digikey = MockDistributor(
        "digikey",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            description="Dual Operational Amplifier",
            category="Operational Amplifiers",
            package="SOIC-8",
            availability=8100,
            source="digikey",
        ),
    )

    orchestrator = EnrichmentOrchestrator(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    result = await orchestrator.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    # Updated assertions for EnrichmentOutcome
    assert result.result is not None
    assert result.result.source == "digikey"
    assert result.result.mpn == "LM358DR"
    assert result.result.availability == 8100

    assert [
        attempt.status
        for attempt in result.attempts
    ] == [
        "NOT_FOUND",
        "NOT_FOUND",
        "ENRICHED",
    ]

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_arrow_success_prevents_digikey_call():
    mouser = MockDistributor(
        "mouser",
        None,
    )

    arrow = MockDistributor(
        "arrow",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="arrow",
        ),
    )

    digikey = MockDistributor(
        "digikey",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="digikey",
        ),
    )

    orchestrator = EnrichmentOrchestrator(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    result = await orchestrator.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    # Updated assertions for EnrichmentOutcome
    assert result.result is not None
    assert result.result.source == "arrow"

    assert [
        attempt.status
        for attempt in result.attempts
    ] == [
        "NOT_FOUND",
        "ENRICHED",
    ]

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 0


@pytest.mark.asyncio
async def test_mouser_success_prevents_all_fallbacks():
    mouser = MockDistributor(
        "mouser",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="mouser",
        ),
    )

    arrow = MockDistributor(
        "arrow",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="arrow",
        ),
    )

    digikey = MockDistributor(
        "digikey",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="digikey",
        ),
    )

    orchestrator = EnrichmentOrchestrator(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    result = await orchestrator.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    # Updated assertions for EnrichmentOutcome
    assert result.result is not None
    assert result.result.source == "mouser"

    assert [
        attempt.status
        for attempt in result.attempts
    ] == [
        "ENRICHED",
    ]

    assert mouser.calls == 1
    assert arrow.calls == 0
    assert digikey.calls == 0


@pytest.mark.asyncio
async def test_all_three_distributors_not_found():
    mouser = MockDistributor(
        "mouser",
        None,
    )

    arrow = MockDistributor(
        "arrow",
        None,
    )

    digikey = MockDistributor(
        "digikey",
        None,
    )

    orchestrator = EnrichmentOrchestrator(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    result = await orchestrator.enrich(
        mpn="UNKNOWN",
        manufacturer="Unknown",
    )

    # Updated assertions for EnrichmentOutcome
    assert result.result is None
    assert result.found is False
    assert result.provider_failed is False
    assert result.all_providers_failed is False

    assert [
        attempt.status
        for attempt in result.attempts
    ] == [
        "NOT_FOUND",
        "NOT_FOUND",
        "NOT_FOUND",
    ]

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1