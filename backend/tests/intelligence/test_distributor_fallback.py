import pytest

from backend.app.intelligence.enrichment.arrow import (
    ArrowProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.enrichment.mouser import (
    MouserProvider,
)
from backend.app.intelligence.enrichment.orchestrator import (
    EnrichmentOrchestrator,
)


class MockMouserProvider(MouserProvider):
    def __init__(
        self,
        result: ComponentEnrichmentResult | None,
    ) -> None:
        self.result = result
        self.calls = 0

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        self.calls += 1
        return self.result


class MockArrowProvider(ArrowProvider):
    def __init__(
        self,
        result: ComponentEnrichmentResult | None,
    ) -> None:
        self.result = result
        self.calls = 0

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        self.calls += 1
        return self.result


@pytest.mark.asyncio
async def test_mouser_not_found_falls_back_to_arrow():
    mouser = MockMouserProvider(
        result=None,
    )

    arrow = MockArrowProvider(
        result=ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            description="Dual Operational Amplifier",
            category="Operational Amplifiers",
            package="SOIC-8",
            manufacturer_part_url=(
                "https://example.com/lm358dr"
            ),
            availability=4200,
            source="arrow",
        ),
    )

    orchestrator = EnrichmentOrchestrator(
        [
            mouser,
            arrow,
        ]
    )

    result = await orchestrator.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    # Updated: use result.result and check attempts status
    assert result.result is not None
    assert result.result.source == "arrow"
    assert result.result.mpn == "LM358DR"
    assert result.result.manufacturer == "Texas Instruments"
    assert result.result.availability == 4200

    assert result.attempts[0].status == "NOT_FOUND"
    assert result.attempts[1].status == "ENRICHED"

    assert mouser.calls == 1
    assert arrow.calls == 1


@pytest.mark.asyncio
async def test_mouser_success_prevents_arrow_call():
    mouser = MockMouserProvider(
        result=ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            description="Dual Operational Amplifier",
            source="mouser",
        ),
    )

    arrow = MockArrowProvider(
        result=ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="arrow",
        ),
    )

    orchestrator = EnrichmentOrchestrator(
        [
            mouser,
            arrow,
        ]
    )

    result = await orchestrator.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    # Updated: use result.result and check attempts status
    assert result.result is not None
    assert result.result.source == "mouser"

    assert result.attempts[0].status == "ENRICHED"

    assert mouser.calls == 1
    assert arrow.calls == 0