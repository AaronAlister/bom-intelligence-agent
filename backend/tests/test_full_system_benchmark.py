import statistics
import time
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.app.agents.bom_agent import BOMAgent
from backend.app.agents.executor import AgentToolExecutor
from backend.app.agents.planner import AgentPlanner
from backend.app.agents.tools.base import AgentTool
from backend.app.agents.tools.bom import BOMIntelligenceTool
from backend.app.api.agent_routes import get_agent
from backend.app.db.session import AsyncSessionLocal
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
from backend.app.main import app
from backend.app.models.bom import BOM
from backend.app.models.bom_component import (
    BOMComponent,
)
from backend.app.models.component import Component


BASE_URL = "http://test"
BENCHMARK_RUNS = 10


class BenchmarkEnrichmentProvider(
    ComponentEnrichmentProvider
):
    """Deterministic enrichment provider for benchmarking."""

    @property
    def name(self) -> str:
        return "benchmark_distributor"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        return ComponentEnrichmentResult(
            mpn=mpn,
            manufacturer=manufacturer,
            description="Benchmark component",
            category="Integrated Circuit",
            package="QFN",
            datasheet_url=None,
            manufacturer_part_url=None,
            availability=5000,
            lifecycle_status="ACTIVE",
            source=self.name,
        )


class BenchmarkQuoteProvider(
    SupplierQuoteProvider
):
    """Deterministic quote provider for benchmarking."""

    @property
    def name(self) -> str:
        return "benchmark_supplier"

    async def quote(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int | None = None,
    ) -> SupplierQuote | None:
        return SupplierQuote(
            supplier=self.name,
            mpn=mpn,
            manufacturer=manufacturer,
            unit_price=1.50,
            currency="USD",
            quantity_available=5000,
            source=self.name,
        )


def build_benchmark_agent() -> BOMAgent:
    """Build the real agent pipeline with deterministic providers."""

    enrichment_provider = (
        BenchmarkEnrichmentProvider()
    )

    quote_provider = (
        BenchmarkQuoteProvider()
    )

    component_service = (
        ComponentIntelligenceService(
            providers=[
                enrichment_provider,
            ],
            quote_providers=[
                quote_provider,
            ],
        )
    )

    bom_service = BOMIntelligenceService(
        component_service=component_service,
    )

    tools: list[AgentTool] = [
        BOMIntelligenceTool(
            bom_service,
        ),
    ]

    return BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(
            tools,
        ),
    )


async def create_benchmark_bom() -> tuple[int, int]:
    """Create one isolated BOM and component for benchmarking."""

    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"BENCHMARK-{suffix}",
        )

        component = Component(
            mpn=f"BENCHMARK-MPN-{suffix}",
            manufacturer="Benchmark Manufacturer",
            description="Benchmark component",
            category="Integrated Circuit",
            package="QFN",
        )

        session.add(bom)
        session.add(component)

        await session.flush()

        bom_component = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=10,
        )

        session.add(bom_component)

        await session.commit()

        return bom.id, component.id


async def delete_benchmark_bom(
    bom_id: int,
    component_id: int,
) -> None:
    """Remove benchmark database records."""

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOMComponent).where(
                BOMComponent.bom_id == bom_id,
            )
        )

        await session.execute(
            delete(Component).where(
                Component.id == component_id,
            )
        )

        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id,
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_full_system_benchmark() -> None:
    """Benchmark repeated execution of the complete agent API path."""

    bom_id, component_id = (
        await create_benchmark_bom()
    )

    latencies_ms: list[float] = []
    successful_runs = 0

    try:
        agent = build_benchmark_agent()

        app.dependency_overrides[
            get_agent
        ] = lambda: agent

        transport = ASGITransport(
            app=app,
        )

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:

            for _ in range(BENCHMARK_RUNS):
                start = time.perf_counter()

                response = await client.post(
                    f"/api/v1/boms/{bom_id}/agent",
                    json={
                        "bom_id": str(bom_id),
                        "task": (
                            "Analyze the complete BOM"
                        ),
                    },
                )

                elapsed_ms = (
                    time.perf_counter()
                    - start
                ) * 1000

                latencies_ms.append(
                    elapsed_ms,
                )

                assert response.status_code == 200

                data = response.json()

                assert (
                    data["status"]
                    == "success"
                )

                assert (
                    data["agent"]
                    == "bom_intelligence_agent"
                )

                assert (
                    data["bom_id"]
                    == str(bom_id)
                )

                assert data["summary"]

                assert data[
                    "execution_metadata"
                ]["planned_tools"] == [
                    "bom_intelligence",
                ]

                assert data[
                    "execution_metadata"
                ]["successful_tools"] == [
                    "bom_intelligence",
                ]

                assert data[
                    "execution_metadata"
                ]["failed_tools"] == []

                assert data[
                    "execution_metadata"
                ]["tool_count"] == 1

                assert data[
                    "execution_metadata"
                ]["successful_tool_count"] == 1

                assert data[
                    "execution_metadata"
                ]["failed_tool_count"] == 0

                successful_runs += 1

        ordered_latencies = sorted(
            latencies_ms,
        )

        mean_ms = statistics.mean(
            latencies_ms,
        )

        median_ms = statistics.median(
            latencies_ms,
        )

        p95_index = min(
            len(ordered_latencies) - 1,
            int(
                len(ordered_latencies)
                * 0.95
            ),
        )

        p95_ms = ordered_latencies[
            p95_index
        ]

        minimum_ms = min(
            latencies_ms,
        )

        maximum_ms = max(
            latencies_ms,
        )

        success_rate = (
            successful_runs
            / BENCHMARK_RUNS
        )

        print()
        print(
            "Full-system agent benchmark:"
        )
        print(
            f"  runs: {BENCHMARK_RUNS}"
        )
        print(
            f"  successful runs: "
            f"{successful_runs}"
        )
        print(
            f"  success rate: "
            f"{success_rate:.2%}"
        )
        print(
            f"  mean latency: "
            f"{mean_ms:.3f} ms"
        )
        print(
            f"  median latency: "
            f"{median_ms:.3f} ms"
        )
        print(
            f"  p95 latency: "
            f"{p95_ms:.3f} ms"
        )
        print(
            f"  minimum latency: "
            f"{minimum_ms:.3f} ms"
        )
        print(
            f"  maximum latency: "
            f"{maximum_ms:.3f} ms"
        )

        assert successful_runs == (
            BENCHMARK_RUNS
        )

        assert success_rate == 1.0

    finally:
        app.dependency_overrides.clear()

        await delete_benchmark_bom(
            bom_id,
            component_id,
        )