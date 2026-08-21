import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.executor import AgentToolExecutor
from backend.app.agents.graph.agent import GraphBOMAgent
from backend.app.agents.tools.bom import (
    BOMIntelligenceTool,
)
from backend.app.agents.tools.component import (
    ComponentIntelligenceTool,
)
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
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component


BASE_URL = "http://test"


class FakeEnrichmentProvider(
    ComponentEnrichmentProvider,
):
    """Deterministic distributor provider for E2E testing."""

    @property
    def name(self) -> str:
        return "e2e_distributor"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        return ComponentEnrichmentResult(
            mpn=mpn,
            manufacturer=manufacturer,
            description="E2E test component",
            category="Integrated Circuit",
            package="QFN",
            datasheet_url=None,
            manufacturer_part_url=None,
            availability=5000,
            lifecycle_status="ACTIVE",
            source=self.name,
        )


class FakeQuoteProvider(
    SupplierQuoteProvider,
):
    """Deterministic supplier quote provider for E2E testing."""

    @property
    def name(self) -> str:
        return "e2e_supplier"

    async def quote(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int | None = None,
    ) -> SupplierQuote | None:
        effective_quantity = quantity or 1

        return SupplierQuote(
            supplier=self.name,
            mpn=mpn,
            manufacturer=manufacturer,
            unit_price=1.50,
            currency="USD",
            quantity_available=max(
                5000,
                effective_quantity,
            ),
        )


def build_e2e_agent(
    session: AsyncSession,
) -> GraphBOMAgent:
    """
    Build the real LangGraph-backed agent using
    deterministic test providers.
    """

    del session

    enrichment_provider = FakeEnrichmentProvider()
    quote_provider = FakeQuoteProvider()

    component_service = ComponentIntelligenceService(
        providers=[enrichment_provider],
        quote_providers=[quote_provider],
    )

    bom_service = BOMIntelligenceService(
        component_service=component_service,
    )

    tools = [
        ComponentIntelligenceTool(
            component_service,
        ),
        BOMIntelligenceTool(
            bom_service,
        ),
    ]

    executor = AgentToolExecutor(tools)

    return GraphBOMAgent(
        executor=executor,
    )


@pytest.mark.asyncio
async def test_agent_end_to_end_real_pipeline() -> None:
    """
    Verify the complete API → LangGraph → planner →
    executor → BOM intelligence → AgentResponse pipeline.
    """

    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"E2E-AGENT-{suffix}",
        )

        component = Component(
            mpn=f"E2E-MPN-{suffix}",
            manufacturer="Test Manufacturer",
            description="E2E component",
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

        bom_id = bom.id
        component_id = component.id

    try:
        async with AsyncSessionLocal() as session:
            agent = build_e2e_agent(session)

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
                response = await client.post(
                    f"/api/v1/boms/{bom_id}/agent",
                    json={
                        "bom_id": str(bom_id),
                        "task": "Analyze the complete BOM",
                    },
                )

        assert response.status_code == 200

        data = response.json()

        assert data["agent"] == (
            "bom_intelligence_agent"
        )

        assert data["status"] == "success"

        assert data["bom_id"] == str(bom_id)

        metadata = data["execution_metadata"]

        # Planner output.
        assert metadata["planned_tools"] == [
            "bom_intelligence",
        ]

        # Executor output.
        assert metadata["successful_tools"] == [
            "bom_intelligence",
        ]

        assert metadata["failed_tools"] == []

        assert metadata["tool_count"] == 1

        assert metadata[
            "successful_tool_count"
        ] == 1

        assert metadata[
            "failed_tool_count"
        ] == 0

        assert metadata["execution_count"] == 1

        # LangGraph execution-plan evidence.
        assert metadata["execution_plan"] is not None

        execution_plan = metadata[
            "execution_plan"
        ]

        assert execution_plan["steps"]

        assert execution_plan["steps"][0][
            "tool_name"
        ] == "bom_intelligence"

        assert execution_plan["steps"][0][
            "status"
        ] == "success"

        # Final agent output.
        assert data["summary"]

        assert len(data["evidence"]) == 1

        assert data["evidence"][0]["source"] == (
            "bom_intelligence"
        )

        assert data["evidence"][0]["source_id"] == (
            str(bom_id)
        )

        assert data["confidence"] == 1.0

    finally:
        app.dependency_overrides.clear()

        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BOMComponent).where(
                    BOMComponent.bom_id == bom_id
                )
            )

            await session.execute(
                delete(Component).where(
                    Component.id == component_id
                )
            )

            await session.execute(
                delete(BOM).where(
                    BOM.id == bom_id
                )
            )

            await session.commit()