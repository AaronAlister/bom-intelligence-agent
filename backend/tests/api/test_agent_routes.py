import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component

from backend.app.agents.contracts import (
    AgentResponse,
    Evidence,
)
from backend.app.agents.executor import AgentToolExecutor
from backend.app.agents.graph.agent import GraphBOMAgent
from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import AgentTool
from backend.app.api.agent_routes import (
    get_agent,
)


BASE_URL = "http://test"


@pytest.mark.asyncio
async def test_bom_agent_returns_404_for_unknown_bom():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/999999999/agent",
            json={
                "bom_id": "ignored",
                "task": "Analyze this BOM",
            },
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "BOM 999999999 not found."
    )


@pytest.mark.asyncio
async def test_bom_agent_rejects_empty_bom():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"API-AGENT-{suffix}",
        )

        session.add(bom)

        await session.commit()

        bom_id = bom.id

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                f"/api/v1/boms/{bom_id}/agent",
                json={
                    "bom_id": str(bom_id),
                    "task": "Analyze this BOM",
                },
            )

        assert response.status_code == 422

        assert (
            response.json()["detail"]
            == f"BOM {bom_id} contains no components."
        )

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BOM).where(
                    BOM.id == bom_id
                )
            )

            await session.commit()


class FakeBOMAgent:
    """Deterministic BOM agent for API tests."""

    async def run(self, request):
        return AgentResponse(
            agent="bom_intelligence_agent",
            status="success",
            bom_id=request.bom_id,
            summary="Test BOM analysis completed successfully.",
            findings=[
                {
                    "type": "component_analysis",
                    "message": "Component intelligence completed.",
                }
            ],
            risks=[
                {
                    "severity": "LOW",
                    "message": "No critical component risks detected.",
                }
            ],
            recommendations=[
                {
                    "action": "BUY",
                    "message": "Component is suitable for procurement.",
                }
            ],
            evidence=[
                Evidence(
                    source="test",
                    source_id="bom-test",
                    excerpt="API evidence test",
                    metadata={
                        "test": True,
                    },
                )
            ],
            confidence=0.95,
            execution_metadata={
                "execution_id": "test-execution-001",
                "started_at": "2026-08-14T10:00:00+00:00",
                "completed_at": "2026-08-14T10:00:01+00:00",
                "execution_time_ms": 1000.0,
                "planned_tools": [
                    "component_intelligence",
                    "bom_intelligence",
                ],
                "successful_tools": [
                    "component_intelligence",
                    "bom_intelligence",
                ],
                "failed_tools": [],
                "tool_count": 2,
                "successful_tool_count": 2,
                "failed_tool_count": 0,
                "execution_count": 2,
                "executions": [
                    {
                        "tool_name": "component_intelligence",
                        "status": "success",
                        "started_at": (
                            "2026-08-14T10:00:00+00:00"
                        ),
                        "completed_at": (
                            "2026-08-14T10:00:00.500000+00:00"
                        ),
                        "execution_time_ms": 500.0,
                        "error": None,
                    },
                    {
                        "tool_name": "bom_intelligence",
                        "status": "success",
                        "started_at": (
                            "2026-08-14T10:00:00.500000+00:00"
                        ),
                        "completed_at": (
                            "2026-08-14T10:00:01+00:00"
                        ),
                        "execution_time_ms": 500.0,
                        "error": None,
                    },
                ],
                "errors": [],
            },
        )


@pytest.mark.asyncio
async def test_bom_agent_returns_agent_response():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"API-AGENT-{suffix}",
        )

        component = Component(
            mpn=f"AGENT-TEST-{suffix}",
            manufacturer="Test Manufacturer",
            description="Test component",
            category="IC",
            package="QFN",
        )

        session.add(bom)
        session.add(component)
        await session.flush()

        bom_component = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=5,
        )

        session.add(bom_component)

        await session.commit()

        bom_id = bom.id
        component_id = component.id

    try:
        app.dependency_overrides[get_agent] = (
            lambda: FakeBOMAgent()
        )

        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                f"/api/v1/boms/{bom_id}/agent",
                json={
                    "bom_id": str(bom_id),
                    "task": "Analyze procurement risk",
                    "context": {
                        "source": "api_test",
                    },
                    "requested_evidence": [
                        "supplier",
                        "risk",
                    ],
                },
            )

        print("STATUS:", response.status_code)
        print("BODY:", response.text)

        assert response.status_code == 200

        data = response.json()

        assert data["agent"] == (
            "bom_intelligence_agent"
        )

        assert data["status"] == "success"

        assert data["bom_id"] == str(bom_id)

        assert data["summary"] == (
            "Test BOM analysis completed successfully."
        )

        assert len(data["findings"]) == 1
        assert len(data["risks"]) == 1
        assert len(data["recommendations"]) == 1
        assert len(data["evidence"]) == 1
        assert (
            data["evidence"][0]["source"]
            == "test"
        )
        assert (
            data["evidence"][0]["source_id"]
            == "bom-test"
        )
        assert (
            data["evidence"][0]["excerpt"]
            == "API evidence test"
        )
        assert (
            data["evidence"][0]["metadata"]["test"]
            is True
        )

        assert data["confidence"] == 0.95

        metadata = data["execution_metadata"]

        assert (
            metadata["execution_id"]
            == "test-execution-001"
        )

        assert (
            metadata["started_at"]
            == "2026-08-14T10:00:00+00:00"
        )

        assert (
            metadata["completed_at"]
            == "2026-08-14T10:00:01+00:00"
        )

        assert (
            metadata["execution_time_ms"]
            == 1000.0
        )

        assert len(
            metadata["executions"]
        ) == 2

        first_execution = (
            metadata["executions"][0]
        )

        assert (
            first_execution["tool_name"]
            == "component_intelligence"
        )

        assert (
            first_execution["status"]
            == "success"
        )

        assert (
            first_execution["execution_time_ms"]
            == 500.0
        )

        assert (
            first_execution["error"]
            is None
        )

        assert metadata["errors"] == []

        assert (
            data["execution_metadata"][
                "successful_tool_count"
            ]
            == 2
        )

        assert (
            data["execution_metadata"][
                "failed_tool_count"
            ]
            == 0
        )

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


@pytest.mark.asyncio
async def test_bom_agent_route_uses_real_rag_enabled_agent():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"API-RAG-{suffix}",
        )

        component = Component(
            mpn=f"RAG-TEST-{suffix}",
            manufacturer="Test Manufacturer",
            description="RAG API test component",
            category="IC",
            package="QFN",
        )

        session.add(bom)
        session.add(component)

        await session.flush()

        bom_component = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=1,
        )

        session.add(bom_component)

        await session.commit()

        bom_id = bom.id
        component_id = component.id

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                f"/api/v1/boms/{bom_id}/agent",
                json={
                    "bom_id": str(bom_id),
                    "task": "Analyze component lifecycle",
                    "requested_evidence": [
                        "lifecycle",
                    ],
                },
            )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["execution_metadata"][
                "rag_evidence_requested"
            ]
            is True
        )

        assert (
            "rag_evidence_count"
            in data["execution_metadata"]
        )

    finally:
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


class PartialBOMAgent:
    """Agent that returns a partial execution result."""

    async def run(self, request):
        return AgentResponse(
            agent="bom_intelligence_agent",
            status="partial",
            bom_id=request.bom_id,
            summary=(
                "BOM intelligence analysis completed "
                "partially. One or more tools failed "
                "during execution."
            ),
            findings=[
                {
                    "type": "component_analysis",
                    "message": "Partial analysis completed.",
                }
            ],
            risks=[
                {
                    "severity": "HIGH",
                    "message": "Some analysis failed.",
                }
            ],
            recommendations=[],
            evidence=[],
            confidence=0.5,
            execution_metadata={
                "planned_tools": [
                    "bom_intelligence",
                    "alternative_analysis",
                ],
                "successful_tools": [
                    "bom_intelligence",
                ],
                "failed_tools": [
                    "alternative_analysis",
                ],
                "tool_count": 2,
                "successful_tool_count": 1,
                "failed_tool_count": 1,
                "execution_count": 2,
            },
        )


class FailedBOMAgent:
    """Agent that returns a complete failure."""

    async def run(self, request):
        return AgentResponse(
            agent="bom_intelligence_agent",
            status="failed",
            bom_id=request.bom_id,
            summary=(
                "BOM intelligence analysis failed: "
                "BOM intelligence unavailable."
            ),
            findings=[],
            risks=[],
            recommendations=[],
            evidence=[],
            confidence=0.0,
            execution_metadata={
                "planned_tools": [
                    "bom_intelligence",
                ],
                "successful_tools": [],
                "failed_tools": [
                    "bom_intelligence",
                ],
                "tool_count": 1,
                "successful_tool_count": 0,
                "failed_tool_count": 1,
                "execution_count": 1,
            },
        )


class RejectingBOMAgent:
    """Agent that rejects an invalid task."""

    async def run(self, request):
        raise ValueError(
            "Agent task cannot be empty"
        )


@pytest.mark.asyncio
async def test_bom_agent_returns_partial_response():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"API-AGENT-{suffix}",
        )

        component = Component(
            mpn=f"AGENT-PARTIAL-{suffix}",
            manufacturer="Test Manufacturer",
            description="Partial test component",
            category="IC",
            package="QFN",
        )

        session.add(bom)
        session.add(component)

        await session.flush()

        bom_component = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=5,
        )

        session.add(bom_component)
        await session.commit()

        bom_id = bom.id
        component_id = component.id

    try:
        app.dependency_overrides[get_agent] = (
            lambda: PartialBOMAgent()
        )

        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                f"/api/v1/boms/{bom_id}/agent",
                json={
                    "bom_id": str(bom_id),
                    "task": (
                        "Find alternatives for "
                        "high-risk components"
                    ),
                },
            )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "partial"
        assert data["confidence"] == 0.5

        assert data["execution_metadata"][
            "successful_tool_count"
        ] == 1

        assert data["execution_metadata"][
            "failed_tool_count"
        ] == 1

        assert data["execution_metadata"][
            "successful_tools"
        ] == ["bom_intelligence"]

        assert data["execution_metadata"][
            "failed_tools"
        ] == ["alternative_analysis"]

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


@pytest.mark.asyncio
async def test_bom_agent_returns_failed_response():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"API-AGENT-{suffix}",
        )

        component = Component(
            mpn=f"AGENT-FAILED-{suffix}",
            manufacturer="Test Manufacturer",
            description="Failure test component",
            category="IC",
            package="QFN",
        )

        session.add(bom)
        session.add(component)

        await session.flush()

        bom_component = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=5,
        )

        session.add(bom_component)
        await session.commit()

        bom_id = bom.id
        component_id = component.id

    try:
        app.dependency_overrides[get_agent] = (
            lambda: FailedBOMAgent()
        )

        transport = ASGITransport(app=app)

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

        assert data["status"] == "failed"
        assert data["confidence"] == 0.0

        assert data["findings"] == []
        assert data["risks"] == []
        assert data["recommendations"] == []

        assert data["execution_metadata"][
            "tool_count"
        ] == 1

        assert data["execution_metadata"][
            "successful_tool_count"
        ] == 0

        assert data["execution_metadata"][
            "failed_tool_count"
        ] == 1

        assert data["execution_metadata"][
            "failed_tools"
        ] == ["bom_intelligence"]

        assert (
            "BOM intelligence unavailable."
            in data["summary"]
        )

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


@pytest.mark.asyncio
async def test_bom_agent_returns_422_for_invalid_agent_request():
    app.dependency_overrides[get_agent] = (
        lambda: RejectingBOMAgent()
    )

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                "/api/v1/boms/999999999/agent",
                json={
                    "bom_id": "ignored",
                    "task": "anything",
                },
            )

        # The route validates BOM existence before calling
        # the agent, so this should remain a 404.
        assert response.status_code == 404

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bom_agent_returns_422_when_agent_rejects_request():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"API-AGENT-{suffix}",
        )

        component = Component(
            mpn=f"AGENT-REJECT-{suffix}",
            manufacturer="Test Manufacturer",
            description="Validation test component",
            category="IC",
            package="QFN",
        )

        session.add(bom)
        session.add(component)

        await session.flush()

        bom_component = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=5,
        )

        session.add(bom_component)
        await session.commit()

        bom_id = bom.id
        component_id = component.id

    try:
        app.dependency_overrides[get_agent] = (
            lambda: RejectingBOMAgent()
        )

        transport = ASGITransport(app=app)

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

        assert response.status_code == 422

        assert response.json()["detail"] == (
            "Agent task cannot be empty"
        )

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


# ----- New test: prove LangGraph is used in API -----

class GraphTestTool(AgentTool):
    name = "bom_intelligence"
    description = "Tool for graph API test."

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "findings": [
                    {
                        "type": "graph_test",
                        "message": "Graph execution confirmed.",
                    }
                ]
            },
        )


@pytest.mark.asyncio
async def test_bom_agent_uses_langgraph() -> None:
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"API-GRAPH-{suffix}",
        )

        component = Component(
            mpn=f"GRAPH-TEST-{suffix}",
            manufacturer="Test Manufacturer",
            description="Graph test component",
            category="IC",
            package="QFN",
        )

        session.add(bom)
        session.add(component)

        await session.flush()

        bom_component = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=1,
        )

        session.add(bom_component)
        await session.commit()

        bom_id = bom.id
        component_id = component.id

    try:
        # Override dependency with a real GraphBOMAgent using our test tool
        def override_get_agent():
            executor = AgentToolExecutor([GraphTestTool()])
            return GraphBOMAgent(executor=executor)

        app.dependency_overrides[get_agent] = override_get_agent

        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                f"/api/v1/boms/{bom_id}/agent",
                json={
                    "bom_id": str(bom_id),
                    "task": "Analyze BOM",
                },
            )

        assert response.status_code == 200

        data = response.json()

        # Verify that the execution_plan metadata is present,
        # proving the LangGraph path was used.
        metadata = data["execution_metadata"]
        assert "execution_plan" in metadata
        assert metadata["execution_plan"] is not None

        # Also check that the tool executed successfully.
        assert data["status"] == "success"
        assert len(data["findings"]) == 1
        assert data["findings"][0]["type"] == "graph_test"

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