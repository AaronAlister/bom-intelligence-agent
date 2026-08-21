import pytest

from backend.app.agents.bom_agent import BOMAgent
from backend.app.agents.contracts import (
    AgentRequest,
    Evidence,
)
from backend.app.agents.executor import AgentToolExecutor
from backend.app.agents.planner import AgentPlanner
from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import AgentTool


class FakeBOMTool(AgentTool):
    """
    Deterministic BOM tool used to verify the agent + RAG
    orchestration boundary.
    """

    name = AgentPlanner.BOM_TOOL
    description = "Fake BOM intelligence tool for integration tests."

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, object],
    ) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "findings": [
                    {
                        "type": "bom_analysis",
                        "message": "BOM analysis completed.",
                    }
                ],
                "risks": [],
                "recommendations": [],
            },
        )


class FakeRAGService:
    """
    Deterministic RAG service used to verify that BOMAgent
    consumes and exposes retrieved evidence correctly.
    """

    def __init__(
        self,
        evidence: list[Evidence],
    ) -> None:
        self.evidence = evidence
        self.queries: list[str] = []

    async def retrieve_evidence(
        self,
        *,
        query: str,
        retrieval_limit: int = 10,
        evidence_limit: int = 5,
    ) -> list[Evidence]:
        self.queries.append(query)

        return self.evidence


@pytest.mark.asyncio
async def test_bom_agent_integrates_rag_evidence():
    evidence = [
        Evidence(
            source="rag",
            source_id="DOC-001-chunk-0",
            excerpt=(
                "The input voltage range is "
                "4.5V to 5.5V."
            ),
            metadata={
                "document_id": "DOC-001",
                "manufacturer": "Acme",
                "mpn": "ACME-PS-001",
            },
        )
    ]

    rag_service = FakeRAGService(
        evidence=evidence,
    )

    agent = BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(
            [FakeBOMTool()]
        ),
        rag_service=rag_service,
    )

    request = AgentRequest(
        bom_id="BOM-E2E-001",
        task="Analyze the complete BOM",
        requested_evidence=[
            "voltage specifications",
        ],
    )

    response = await agent.run(request)

    assert response.status == "success"

    assert response.bom_id == "BOM-E2E-001"

    assert len(response.findings) == 1

    assert len(response.evidence) == 1

    retrieved_evidence = response.evidence[0]

    assert retrieved_evidence.source == "rag"
    assert retrieved_evidence.source_id == (
        "DOC-001-chunk-0"
    )

    assert retrieved_evidence.excerpt == (
        "The input voltage range is "
        "4.5V to 5.5V."
    )

    assert retrieved_evidence.metadata["document_id"] == (
        "DOC-001"
    )

    assert retrieved_evidence.metadata["manufacturer"] == (
        "Acme"
    )

    assert retrieved_evidence.metadata["mpn"] == (
        "ACME-PS-001"
    )

    assert response.execution_metadata[
        "rag_evidence_requested"
    ] is True

    assert response.execution_metadata[
        "rag_evidence_count"
    ] == 1

    assert response.execution_metadata[
        "planned_tools"
    ] == [
        AgentPlanner.BOM_TOOL
    ]

    assert response.execution_metadata[
        "execution_count"
    ] == 1

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 1

    assert response.execution_metadata[
        "failed_tool_count"
    ] == 0

    assert response.execution_metadata[
        "executions"
    ][0]["tool_name"] == AgentPlanner.BOM_TOOL

    assert response.execution_metadata[
        "executions"
    ][0]["status"] == "success"

    assert response.execution_metadata[
        "errors"
    ] == []

    assert len(rag_service.queries) == 1

    assert rag_service.queries[0] == (
        "Analyze the complete BOM voltage specifications"
    )


@pytest.mark.asyncio
async def test_bom_agent_returns_partial_when_rag_fails():
    class FailingRAGService:
        async def retrieve_evidence(
            self,
            *,
            query: str,
            retrieval_limit: int = 10,
            evidence_limit: int = 5,
        ) -> list[Evidence]:
            raise RuntimeError(
                "RAG backend unavailable"
            )

    agent = BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(
            [FakeBOMTool()]
        ),
        rag_service=FailingRAGService(),
    )

    request = AgentRequest(
        bom_id="BOM-E2E-002",
        task="Analyze the complete BOM",
        requested_evidence=[
            "datasheet specifications",
        ],
    )

    response = await agent.run(request)

    assert response.status == "partial"

    assert response.execution_metadata[
        "rag_evidence_requested"
    ] is True

    assert response.execution_metadata[
        "rag_evidence_count"
    ] == 0

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 1

    assert response.execution_metadata[
        "errors"
    ] == [
        "RAG evidence retrieval failed: "
        "RAG backend unavailable"
    ]

    assert len(response.evidence) == 0