import pytest
from typing import cast

from backend.app.intelligence.availability.supplier.base import (
    SupplierQuoteProvider,
)
from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
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
from backend.app.intelligence.lifecycle.models import (
    LifecycleRisk,
    LifecycleStatus,
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


class MockSupplier(
    SupplierQuoteProvider,
):
    def __init__(
        self,
        supplier_name: str,
        result: SupplierQuote | None,
    ) -> None:
        self._name = supplier_name
        self._result = result
        self.calls = 0
        self.received_quantity = None

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
        self.calls += 1
        self.received_quantity = quantity
        return self._result


@pytest.mark.asyncio
async def test_component_intelligence_combines_procurement_and_lifecycle():
    mouser = MockProvider(
        "mouser",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=5000,
            lifecycle_status="ACTIVE",
            source="mouser",
        ),
    )

    arrow = MockProvider(
        "arrow",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=4200,
            lifecycle_status="ACTIVE",
            source="arrow",
        ),
    )

    digikey = MockProvider(
        "digikey",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            availability=8100,
            lifecycle_status="ACTIVE",
            source="digikey",
        ),
    )

    mouser_quote = MockSupplier(
        "mouser",
        SupplierQuote(
            supplier="mouser",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.72,
            currency="USD",
            quantity_available=5000,
            moq=10,
            order_multiple=10,
            lead_time_days=14,
            source="mouser",
        ),
    )

    arrow_quote = MockSupplier(
        "arrow",
        SupplierQuote(
            supplier="arrow",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.85,
            currency="USD",
            quantity_available=4200,
            moq=10,
            order_multiple=10,
            lead_time_days=10,
            source="arrow",
        ),
    )

    digikey_quote = MockSupplier(
        "digikey",
        SupplierQuote(
            supplier="digikey",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.60,
            currency="USD",
            quantity_available=8100,
            moq=10,
            order_multiple=10,
            lead_time_days=5,
            source="digikey",
        ),
    )

    service = ComponentIntelligenceService(
        [
            mouser,
            arrow,
            digikey,
        ],
        [
            mouser_quote,
            arrow_quote,
            digikey_quote,
        ],
    )

    result = await service.analyze(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=100,
    )

    assert result.risk is not None
    assert result.decision is not None

    assert result.mpn == "LM358DR"

    assert (
        result.manufacturer
        == "Texas Instruments"
    )

    assert (
        result.procurement
        .availability
        .total_distributor_quantity
        == 17300
    )

    assert (
        result.procurement
        .availability
        .best_available_quantity
        == 8100
    )

    assert (
        result.lifecycle.status
        == LifecycleStatus.ACTIVE
    )

    assert (
        result.lifecycle.risk
        == LifecycleRisk.LOW
    )

    assert (
        result.lifecycle.source
        == "mouser"
    )

    assert result.risk.score == 0.0
    assert result.risk.severity.value == "LOW"

    assert result.decision.action == DecisionAction.BUY
    assert result.decision.supplier == "digikey"
    assert result.decision.estimated_unit_price == 1.60
    assert result.decision.estimated_total_cost == 160.00
    assert result.decision.currency == "USD"

    assert mouser_quote.calls == 1
    assert arrow_quote.calls == 1
    assert digikey_quote.calls == 1

    assert mouser_quote.received_quantity == 100
    assert arrow_quote.received_quantity == 100
    assert digikey_quote.received_quantity == 100

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_component_intelligence_detects_lifecycle_risk():
    mouser = MockProvider(
        "mouser",
        ComponentEnrichmentResult(
            mpn="OLD-PART",
            manufacturer="Test Manufacturer",
            availability=100,
            lifecycle_status="EOL",
            source="mouser",
        ),
    )

    arrow = MockProvider(
        "arrow",
        ComponentEnrichmentResult(
            mpn="OLD-PART",
            manufacturer="Test Manufacturer",
            availability=0,
            lifecycle_status="EOL",
            source="arrow",
        ),
    )

    digikey = MockProvider(
        "digikey",
        None,
    )

    quote_provider = MockSupplier(
        "mouser",
        SupplierQuote(
            supplier="mouser",
            manufacturer="Test Manufacturer",
            mpn="OLD-PART",
            unit_price=2.00,
            currency="USD",
            quantity_available=100,
            source="mouser",
        ),
    )

    service = ComponentIntelligenceService(
        [
            mouser,
            arrow,
            digikey,
        ],
        [
            quote_provider,
        ],
    )

    result = await service.analyze(
        mpn="OLD-PART",
        manufacturer="Test Manufacturer",
        quantity=100,
    )

    assert result.risk is not None
    assert result.decision is not None

    assert (
        result.lifecycle.status
        == LifecycleStatus.EOL
    )

    assert (
        result.lifecycle.risk
        == LifecycleRisk.HIGH
    )

    assert (
        result.procurement
        .availability
        .total_distributor_quantity
        == 100
    )

    assert result.risk.score == 68.0
    assert result.risk.severity.value == "HIGH"

    assert result.risk.lifecycle_score == 80.0
    assert result.risk.availability_score == 50.0

    assert result.decision.action == DecisionAction.REVIEW
    assert result.decision.supplier == "mouser"


@pytest.mark.asyncio
async def test_component_intelligence_handles_no_distributor_results():
    mock_providers: list[MockProvider] = [
        MockProvider("mouser", None),
        MockProvider("arrow", None),
        MockProvider("digikey", None),
    ]

    quote_provider = MockSupplier(
        "mouser",
        None,
    )

    service = ComponentIntelligenceService(
        cast(
            list[ComponentEnrichmentProvider],
            mock_providers,
        ),
        [
            quote_provider,
        ],
    )

    result = await service.analyze(
        mpn="UNKNOWN",
        manufacturer="Unknown",
        quantity=100,
    )

    assert result.risk is not None
    assert result.decision is not None

    assert result.procurement.distributor_results == []

    assert (
        result.procurement
        .availability
        .procurement_status
        .value
        == "UNKNOWN"
    )

    assert (
        result.lifecycle.status
        == LifecycleStatus.UNKNOWN
    )

    assert (
        result.lifecycle.risk
        == LifecycleRisk.UNKNOWN
    )

    assert result.risk.score == 25.0
    assert result.risk.severity.value == "MEDIUM"

    assert (
        result.decision.action
        == DecisionAction.SOURCE_ALTERNATIVE
    )

    assert result.decision.supplier is None

    for provider in mock_providers:
        assert provider.calls == 1


@pytest.mark.asyncio
async def test_component_intelligence_rejects_invalid_quantity():
    service = ComponentIntelligenceService(
        [
            MockProvider(
                "mouser",
                None,
            )
        ],
        [
            MockSupplier(
                "mouser",
                None,
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="Quantity must be greater than zero",
    ):
        await service.analyze(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            quantity=0,
        )