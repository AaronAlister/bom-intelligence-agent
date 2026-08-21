from typing import Any

import pytest

from backend.app.agents.bom_agent import BOMAgent
from backend.app.agents.contracts import AgentRequest
from backend.app.agents.executor import AgentToolExecutor
from backend.app.agents.planner import AgentPlanner
from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import AgentTool


class SuccessfulObservabilityTool(AgentTool):
    name = "bom_intelligence"
    description = "Test tool for observability."

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
            data={},
        )


def build_agent(
    tools: list[AgentTool] | None = None,
) -> BOMAgent:
    if tools is None:
        tools = [SuccessfulObservabilityTool()]
    return BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(tools),
    )


@pytest.mark.asyncio
async def test_agent_exposes_tool_execution_details():
    agent = build_agent()
    response = await agent.run(
        AgentRequest(
            bom_id="BOM-OBS-002",
            task="Analyze the complete BOM",
        )
    )
    executions = response.execution_metadata[
        "executions"
    ]
    assert len(executions) == 1
    execution = executions[0]
    assert (
        execution["tool_name"]
        == "bom_intelligence"
    )
    assert execution["status"] == "success"
    assert execution["started_at"] is not None
    assert execution["completed_at"] is not None
    assert execution["execution_time_ms"] >= 0
    assert execution["error"] is None


@pytest.mark.asyncio
async def test_agent_execution_id_is_unique():
    agent = build_agent()
    request = AgentRequest(
        bom_id="BOM-OBS-003",
        task="Analyze the complete BOM",
    )
    first = await agent.run(request)
    second = await agent.run(request)
    assert (
        first.execution_metadata["execution_id"]
        != second.execution_metadata["execution_id"]
    )


@pytest.mark.asyncio
async def test_agent_exposes_errors():
    agent = BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor([]),
    )
    response = await agent.run(
        AgentRequest(
            bom_id="BOM-OBS-004",
            task="Analyze the complete BOM",
        )
    )
    metadata = response.execution_metadata
    assert metadata["errors"]
    assert (
        "not registered"
        in metadata["errors"][0]
    )

@pytest.mark.asyncio
async def test_agent_exposes_execution_plan() -> None:
    agent = build_agent()

    response = await agent.run(
        AgentRequest(
            bom_id="BOM-OBS-005",
            task="Analyze the complete BOM",
        )
    )

    metadata = response.execution_metadata

    execution_plan = metadata.get(
        "execution_plan"
    )

    assert execution_plan is not None

    assert execution_plan["steps"]

    assert (
        execution_plan["steps"][0]["tool_name"]
        == "bom_intelligence"
    )

    assert (
        execution_plan["steps"][0]["status"]
        == "success"
    )