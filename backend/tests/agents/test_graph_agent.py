import pytest

from backend.app.agents.contracts import (
    AgentRequest,
)
from backend.app.agents.graph.agent import (
    GraphBOMAgent,
)
from backend.app.agents.executor import (
    AgentToolExecutor,
)
from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import AgentTool
from typing import Any


class GraphExecutionTool(AgentTool):
    name = "bom_intelligence"
    description = "Deterministic graph execution test tool."

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
                "bom_id": bom_id,
                "executed_by": "graph",
            },
        )


@pytest.mark.asyncio
async def test_graph_bom_agent_returns_agent_response() -> None:
    agent = GraphBOMAgent(
        executor=AgentToolExecutor(
            [GraphExecutionTool()]
        )
    )

    response = await agent.run(
        AgentRequest(
            bom_id="GRAPH-AGENT-001",
            task="Analyze the complete BOM",
        )
    )

    assert response.agent == (
        "bom_intelligence_agent"
    )

    assert response.bom_id == (
        "GRAPH-AGENT-001"
    )

    assert response.status in {
        "success",
        "partial",
        "failed",
    }

    assert response.execution_metadata[
        "execution_plan"
    ] is not None