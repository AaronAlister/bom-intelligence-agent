from typing import cast

import pytest

from backend.app.intelligence.bom.service import (
    BOMIntelligenceService,
)
from backend.app.intelligence.component.service import (
    ComponentIntelligenceService,
)
from backend.app.intelligence.decision.models import (
    DecisionAction,
)
from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.availability.supplier.base import (
    SupplierQuoteProvider,
)
from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)


class MockDistributor(
    ComponentEnrichmentProvider
):
    def __init__(
        self,
        name: str,
        result: ComponentEnrichmentResult,
    ) -> None:
        self._name = name
        self._result = result

    @property
    def name(self) -> str:
        return self._name

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        return self._result


class MockSupplier(
    SupplierQuoteProvider
):
    def __init__(
        self,
        name: str,
        quote: SupplierQuote,
    ) -> None:
        self._name = name
        self._quote = quote

    @property
    def name(self) -> str:
        return self._name

    async def quote(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int | None = None,
    ) -> SupplierQuote | None:
        return self._quote


def make_component_service() -> (
    ComponentIntelligenceService
):
    distributors = [
        MockDistributor(
            "mouser",
            ComponentEnrichmentResult(
                mpn="LM358DR",
                manufacturer="Texas Instruments",
                availability=5000,
                lifecycle_status="ACTIVE",
                source="mouser",
            ),
        ),
        MockDistributor(
            "arrow",
            ComponentEnrichmentResult(
                mpn="LM358DR",
                manufacturer="Texas Instruments",
                availability=4200,
                lifecycle_status="ACTIVE",
                source="arrow",
            ),
        ),
    ]

    suppliers = [
        MockSupplier(
            "mouser",
            SupplierQuote(
                supplier="mouser",
                manufacturer="Texas Instruments",
                mpn="LM358DR",
                unit_price=1.72,
                currency="USD",
                quantity_available=5000,
                source="mouser",
            ),
        )
    ]

    return ComponentIntelligenceService(
        cast(
            list[ComponentEnrichmentProvider],
            distributors,
        ),
        cast(
            list[SupplierQuoteProvider],
            suppliers,
        ),
    )


@pytest.mark.asyncio
async def test_bom_intelligence_aggregates_components():
    service = BOMIntelligenceService(
        make_component_service()
    )

    result = await service.analyze(
        components=[
            (
                1,
                "LM358DR",
                "Texas Instruments",
                100,
            ),
            (
                2,
                "LM358DR",
                "Texas Instruments",
                50,
            ),
        ]
    )

    assert len(result.components) == 2

    assert result.components[0].component_id == 1
    assert result.components[0].mpn == "LM358DR"
    assert result.components[0].quantity == 100

    assert result.components[1].component_id == 2
    assert result.components[1].quantity == 50


@pytest.mark.asyncio
async def test_bom_intelligence_calculates_cost():
    service = BOMIntelligenceService(
        make_component_service()
    )

    result = await service.analyze(
        components=[
            (
                1,
                "LM358DR",
                "Texas Instruments",
                100,
            )
        ]
    )

    assert result.cost.total_cost == 172.00
    assert result.cost.currency == "USD"

    assert len(result.cost.components) == 1

    assert (
        result.cost.components[0].total_cost
        == 172.00
    )


@pytest.mark.asyncio
async def test_bom_intelligence_calculates_risk():
    service = BOMIntelligenceService(
        make_component_service()
    )

    result = await service.analyze(
        components=[
            (
                1,
                "LM358DR",
                "Texas Instruments",
                100,
            )
        ]
    )

    assert result.risk.component_count == 1
    assert result.risk.overall_score == 0.0
    assert result.risk.severity == RiskSeverity.LOW

    assert result.risk.high_risk_count == 0
    assert result.risk.critical_count == 0


@pytest.mark.asyncio
async def test_bom_intelligence_contains_component_decision():
    service = BOMIntelligenceService(
        make_component_service()
    )

    result = await service.analyze(
        components=[
            (
                1,
                "LM358DR",
                "Texas Instruments",
                100,
            )
        ]
    )

    decision = (
        result.components[0]
        .intelligence
        .decision
    )

    assert decision is not None
    assert decision.action == DecisionAction.BUY
    assert decision.supplier == "mouser"


@pytest.mark.asyncio
async def test_bom_intelligence_requires_components():
    service = BOMIntelligenceService(
        make_component_service()
    )

    with pytest.raises(
        ValueError,
        match="At least one BOM component",
    ):
        await service.analyze(
            components=[]
        )


@pytest.mark.asyncio
async def test_bom_intelligence_rejects_invalid_quantity():
    service = BOMIntelligenceService(
        make_component_service()
    )

    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        await service.analyze(
            components=[
                (
                    1,
                    "LM358DR",
                    "Texas Instruments",
                    0,
                )
            ]
        )