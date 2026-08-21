import pytest

from backend.app.intelligence.availability.models import (
    ProcurementStatus,
)
from backend.app.intelligence.availability.procurement_service import (
    ComponentProcurementService,
)
from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


class MockProvider(ComponentEnrichmentProvider):
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
async def test_component_procurement_aggregates_all_distributors():
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

    service = ComponentProcurementService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    result = await service.analyze(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert result.mpn == "LM358DR"

    assert (
        result.manufacturer
        == "Texas Instruments"
    )

    assert len(
        result.distributor_results
    ) == 3

    assert [
        item.source
        for item in result.distributor_results
    ] == [
        "mouser",
        "arrow",
        "digikey",
    ]

    assert (
        result.availability
        .total_distributor_quantity
        == 17300
    )

    assert (
        result.availability
        .best_available_quantity
        == 8100
    )

    assert (
        result.availability
        .procurement_status
        == ProcurementStatus.READY
    )

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_component_procurement_handles_partial_results():
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
        None,
    )

    digikey = MockProvider(
        "digikey",
        None,
    )

    service = ComponentProcurementService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    result = await service.analyze(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert len(
        result.distributor_results
    ) == 1

    assert (
        result.distributor_results[0].source
        == "mouser"
    )

    assert (
        result.availability
        .total_distributor_quantity
        == 5000
    )

    assert (
        result.availability
        .procurement_status
        == ProcurementStatus.READY
    )

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_component_procurement_handles_no_results():
    mouser = MockProvider(
        "mouser",
        None,
    )

    arrow = MockProvider(
        "arrow",
        None,
    )

    digikey = MockProvider(
        "digikey",
        None,
    )

    service = ComponentProcurementService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    result = await service.analyze(
        mpn="UNKNOWN",
        manufacturer="Unknown",
    )

    assert result.distributor_results == []

    assert (
        result.availability
        .total_distributor_quantity
        == 0
    )

    assert (
        result.availability
        .best_available_quantity
        is None
    )

    assert (
        result.availability
        .procurement_status
        == ProcurementStatus.UNKNOWN
    )