from typing import Any

import pytest

from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import AgentTool


class DummyTool(AgentTool):
    name = "dummy"
    description = "Test tool."

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
                "component_count": len(component_ids),
            },
        )


@pytest.mark.asyncio
async def test_agent_tool_contract():
    tool = DummyTool()

    result = await tool.execute(
        bom_id="BOM-001",
        component_ids=["1", "2"],
        context={},
    )

    assert result.tool_name == "dummy"
    assert result.status == "success"
    assert result.data["bom_id"] == "BOM-001"
    assert result.data["component_count"] == 2


def test_agent_tool_requires_execute():
    assert "execute" in AgentTool.__abstractmethods__