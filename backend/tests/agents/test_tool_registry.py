import pytest

from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import AgentTool
from backend.app.agents.tools.registry import AgentToolRegistry


class FirstTool(AgentTool):
    name = "first"
    description = "First test tool."
    dependencies: tuple[str, ...] = ()

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, object],
    ) -> ToolResult:
        raise NotImplementedError


class DependentTool(AgentTool):
    name = "dependent"
    description = "Dependent test tool."
    dependencies: tuple[str, ...] = ("first",)

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, object],
    ) -> ToolResult:
        raise NotImplementedError


def test_registry_registers_and_retrieves_tool() -> None:
    tool = FirstTool()
    registry = AgentToolRegistry()

    registry.register(tool)

    assert registry.contains("first")
    assert registry.get("first") is tool


def test_registry_preserves_registration_order() -> None:
    registry = AgentToolRegistry(
        [
            FirstTool(),
            DependentTool(),
        ]
    )

    assert registry.names() == (
        "first",
        "dependent",
    )


def test_registry_rejects_duplicate_tool_names() -> None:
    registry = AgentToolRegistry()

    registry.register(FirstTool())

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(FirstTool())


def test_registry_rejects_unknown_tool() -> None:
    registry = AgentToolRegistry()

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        registry.get("unknown")


def test_registry_returns_tool_metadata() -> None:
    registry = AgentToolRegistry(
        [
            FirstTool(),
            DependentTool(),
        ]
    )

    metadata = registry.metadata("dependent")

    assert metadata.name == "dependent"
    assert metadata.description == "Dependent test tool."
    assert metadata.dependencies == ("first",)


def test_registry_returns_all_metadata() -> None:
    registry = AgentToolRegistry(
        [
            FirstTool(),
            DependentTool(),
        ]
    )

    metadata = registry.all_metadata()

    assert len(metadata) == 2
    assert metadata[0].name == "first"
    assert metadata[1].name == "dependent"
    assert metadata[1].dependencies == ("first",)