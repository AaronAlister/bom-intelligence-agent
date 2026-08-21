import time
from typing import cast

import pytest

from backend.app.intelligence.availability.supplier.base import (
    SupplierQuoteProvider,
)
from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.bom.service import (
    BOMIntelligenceService,
)
from backend.app.intelligence.component.service import (
    ComponentIntelligenceService,
)
from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


class BenchmarkDistributor(
    ComponentEnrichmentProvider
):
    """Deterministic distributor for benchmark execution."""

    def __init__(
        self,
        name: str,
    ) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        return ComponentEnrichmentResult(
            mpn=mpn,
            manufacturer=manufacturer,
            availability=1000,
            lifecycle_status="ACTIVE",
            source=self._name,
        )


class BenchmarkSupplier(
    SupplierQuoteProvider
):
    """Deterministic supplier for benchmark execution."""

    def __init__(
        self,
        name: str,
    ) -> None:
        self._name = name

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
        return SupplierQuote(
            supplier=self._name,
            manufacturer=manufacturer,
            mpn=mpn,
            unit_price=1.00,
            currency="USD",
            quantity_available=1000,
            source=self._name,
        )


def make_benchmark_service() -> BOMIntelligenceService:
    distributors = [
        BenchmarkDistributor("mouser"),
        BenchmarkDistributor("arrow"),
    ]

    suppliers = [
        BenchmarkSupplier("mouser"),
    ]

    component_service = ComponentIntelligenceService(
        cast(
            list[ComponentEnrichmentProvider],
            distributors,
        ),
        cast(
            list[SupplierQuoteProvider],
            suppliers,
        ),
    )

    return BOMIntelligenceService(
        component_service,
    )


def make_benchmark_components() -> list[
    tuple[int, str, str | None, int]
]:
    return [
        (
            1,
            "LM358DR",
            "Texas Instruments",
            4,
        ),
        (
            2,
            "STM32F401C8T6",
            "STMicroelectronics",
            1,
        ),
        (
            3,
            "GRM188R71C104KA01D",
            "Murata",
            12,
        ),
        (
            4,
            "RC0603FR-0710KL",
            "Yageo",
            8,
        ),
        (
            5,
            "TPS62160DQCR",
            "Texas Instruments",
            3,
        ),
        (
            6,
            "MCP1700-3302E/TO",
            "Microchip",
            2,
        ),
        (
            7,
            "SN74HC595N",
            "Texas Instruments",
            2,
        ),
        (
            8,
            "AT24C256C-SSHM-T",
            "Microchip",
            1,
        ),
        (
            9,
            "W25Q64JVSSIQ",
            "Winbond",
            2,
        ),
        (
            10,
            "BSS138",
            "onsemi",
            6,
        ),
        (
            11,
            "1N4148W",
            "onsemi",
            10,
        ),
        (
            12,
            "CGA1A2X7R1H104K",
            "TDK",
            10,
        ),
        (
            13,
            "GRM21BR61C106KE15L",
            "Murata",
            6,
        ),
        (
            14,
            "RC0402FR-0710KL",
            "Yageo",
            20,
        ),
        (
            15,
            "CRCW060310K0FKEA",
            "Vishay",
            12,
        ),
        (
            16,
            "Molex-53261-0271",
            "Molex",
            4,
        ),
        (
            17,
            "USBLC6-2SC6",
            "STMicroelectronics",
            3,
        ),
        (
            18,
            "LTC4412ES6-1",
            "Analog Devices",
            1,
        ),
        (
            19,
            "LM1117IMPX-3.3",
            "Texas Instruments",
            2,
        ),
        (
            20,
            "DS18B20+",
            "Analog Devices",
            2,
        ),
        (
            21,
            "SG-8002CE",
            "Epson",
            1,
        ),
        (
            22,
            "TLV9062IDR",
            "Texas Instruments",
            3,
        ),
        (
            23,
            "SN74LVC1G17DBVR",
            "Texas Instruments",
            4,
        ),
        (
            24,
            "ESP32-WROOM-32E",
            "Espressif",
            1,
        ),
        (
            25,
            "TPS54202DDCR",
            "Texas Instruments",
            2,
        ),
    ]


@pytest.mark.asyncio
async def test_bom_intelligence_benchmark() -> None:
    service = make_benchmark_service()
    components = make_benchmark_components()

    start = time.perf_counter()

    result = await service.analyze(
        components=components,
    )

    elapsed_ms = (
        time.perf_counter() - start
    ) * 1000

    component_count = len(
        result.components
    )

    procurement_count = sum(
        component.intelligence.procurement
        is not None
        for component in result.components
    )

    lifecycle_count = sum(
        component.intelligence.lifecycle
        is not None
        for component in result.components
    )

    risk_count = sum(
        component.intelligence.risk
        is not None
        for component in result.components
    )

    decision_count = sum(
        component.intelligence.decision
        is not None
        for component in result.components
    )

    supplier_decision_count = sum(
        component.intelligence.decision
        is not None
        and component.intelligence.decision.supplier
        is not None
        for component in result.components
    )

    print()
    print(
        "BOM intelligence benchmark:"
    )
    print(
        f"  components: {component_count}"
    )
    print(
        f"  procurement results: "
        f"{procurement_count}"
    )
    print(
        f"  lifecycle assessments: "
        f"{lifecycle_count}"
    )
    print(
        f"  risk assessments: "
        f"{risk_count}"
    )
    print(
        f"  decisions: {decision_count}"
    )
    print(
        f"  supplier-backed decisions: "
        f"{supplier_decision_count}"
    )
    print(
        f"  total cost: "
        f"{result.cost.total_cost}"
    )
    print(
        f"  currency: {result.cost.currency}"
    )
    print(
        f"  BOM risk score: "
        f"{result.risk.overall_score}"
    )
    print(
        f"  BOM risk severity: "
        f"{result.risk.severity}"
    )
    print(
        f"  elapsed: {elapsed_ms:.3f} ms"
    )
    print(
        f"  avg/component: "
        f"{elapsed_ms / component_count:.3f} ms"
    )

    assert component_count == 25
    assert procurement_count == 25
    assert lifecycle_count == 25
    assert risk_count == 25
    assert decision_count == 25
    assert supplier_decision_count == 25