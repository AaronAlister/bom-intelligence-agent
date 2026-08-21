from typing import Any

import pytest

from backend.app.agents.contracts import AgentRequest
from backend.app.agents.planner import AgentPlanner
from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import AgentTool
from backend.app.agents.tools.registry import (
    AgentToolRegistry,
)


@pytest.fixture
def planner() -> AgentPlanner:
    return AgentPlanner()


def make_request(task: str) -> AgentRequest:
    return AgentRequest(
        bom_id="BOM-001",
        task=task,
    )


class PlannerTestTool(AgentTool):
    def __init__(
        self,
        name: str,
        description: str,
        dependencies: tuple[str, ...] = (),
    ) -> None:
        self.name = name
        self.description = description
        self.dependencies = dependencies

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
        )


@pytest.fixture
def registry() -> AgentToolRegistry:
    return AgentToolRegistry(
        [
            PlannerTestTool(
                "component_intelligence",
                "Component supplier and lifecycle intelligence.",
            ),
            PlannerTestTool(
                "bom_intelligence",
                "BOM-level cost and risk intelligence.",
            ),
            PlannerTestTool(
                "alternative_analysis",
                "Alternative component analysis.",
                dependencies=(
                    "bom_intelligence",
                ),
            ),
        ]
    )


def test_complete_bom_analysis_selects_bom_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request("Analyze the complete BOM")
    )

    assert tools == [
        AgentPlanner.BOM_TOOL
    ]


def test_bom_risk_selects_bom_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Analyze procurement risk across the BOM"
        )
    )

    assert tools == [
        AgentPlanner.BOM_TOOL
    ]


def test_component_availability_selects_component_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Check component availability"
        )
    )

    assert tools == [
        AgentPlanner.COMPONENT_TOOL
    ]


def test_component_supplier_request_selects_component_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Evaluate supplier quotes for this component"
        )
    )

    assert tools == [
        AgentPlanner.COMPONENT_TOOL
    ]


def test_alternative_request_selects_alternative_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Find alternative components"
        )
    )

    assert tools == [
        AgentPlanner.ALTERNATIVE_TOOL
    ]


def test_risk_based_alternative_request_selects_bom_then_alternative(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Find alternatives for high-risk components"
        )
    )

    assert tools == [
        AgentPlanner.BOM_TOOL,
        AgentPlanner.ALTERNATIVE_TOOL,
    ]


def test_empty_task_is_rejected(
    planner: AgentPlanner,
):
    with pytest.raises(
        ValueError,
        match="Agent task cannot be empty",
    ):
        planner.plan(
            make_request("")
        )


def test_unknown_task_defaults_to_bom_intelligence(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Give me an analysis"
        )
    )

    assert tools == [
        AgentPlanner.BOM_TOOL
    ]


def test_supplier_pricing_selects_component_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Compare supplier pricing"
        )
    )
    assert tools == [
        AgentPlanner.COMPONENT_TOOL
    ]


def test_total_cost_selects_bom_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Calculate the total cost of the BOM"
        )
    )
    assert tools == [
        AgentPlanner.BOM_TOOL
    ]


def test_available_component_selects_component_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Find available components"
        )
    )
    assert tools == [
        AgentPlanner.COMPONENT_TOOL
    ]


def test_supplier_quotes_selects_component_tool(
    planner: AgentPlanner,
):
    tools = planner.plan(
        make_request(
            "Compare supplier quotes"
        )
    )
    assert tools == [
        AgentPlanner.COMPONENT_TOOL
    ]


def test_create_execution_plan_for_bom_analysis(
    planner: AgentPlanner,
) -> None:
    plan = planner.create_execution_plan(
        make_request("Analyze the complete BOM")
    )

    assert len(plan.steps) == 1

    step = plan.steps[0]

    assert step.step_id == "step_1"
    assert step.tool_name == (
        AgentPlanner.BOM_TOOL
    )
    assert step.dependencies == []
    assert step.status == "pending"


def test_create_execution_plan_for_risk_based_alternatives(
    planner: AgentPlanner,
) -> None:
    plan = planner.create_execution_plan(
        make_request(
            "Find alternatives for high-risk components"
        )
    )

    assert len(plan.steps) == 2

    first_step = plan.steps[0]
    second_step = plan.steps[1]

    assert first_step.step_id == "step_1"
    assert first_step.tool_name == (
        AgentPlanner.BOM_TOOL
    )
    assert first_step.dependencies == []

    assert second_step.step_id == "step_2"
    assert second_step.tool_name == (
        AgentPlanner.ALTERNATIVE_TOOL
    )
    assert second_step.dependencies == [
        "step_1"
    ]


def test_create_execution_plan_preserves_tool_order(
    planner: AgentPlanner,
) -> None:
    plan = planner.create_execution_plan(
        make_request(
            "Find alternatives for high-risk components"
        )
    )

    assert [
        step.tool_name
        for step in plan.steps
    ] == [
        AgentPlanner.BOM_TOOL,
        AgentPlanner.ALTERNATIVE_TOOL,
    ]


def test_create_execution_plan_records_metadata(
    planner: AgentPlanner,
) -> None:
    plan = planner.create_execution_plan(
        make_request("Analyze the complete BOM")
    )

    assert plan.metadata["task"] == (
        "Analyze the complete BOM"
    )
    assert plan.metadata["tool_count"] == 1


def test_planner_validates_registered_tools(
    registry: AgentToolRegistry,
) -> None:
    planner = AgentPlanner(
        registry
    )

    tools = planner.plan(
        make_request(
            "Analyze the complete BOM"
        )
    )

    assert tools == [
        AgentPlanner.BOM_TOOL
    ]


def test_planner_exposes_available_capabilities(
    registry: AgentToolRegistry,
) -> None:
    planner = AgentPlanner(
        registry
    )

    assert planner.available_capabilities() == (
        "component_intelligence",
        "bom_intelligence",
        "alternative_analysis",
    )


def test_planner_exposes_capability_metadata(
    registry: AgentToolRegistry,
) -> None:
    planner = AgentPlanner(
        registry
    )

    metadata = planner.capability_metadata()

    assert [
        item.name
        for item in metadata
    ] == [
        "component_intelligence",
        "bom_intelligence",
        "alternative_analysis",
    ]

    alternative_metadata = metadata[2]

    assert alternative_metadata.dependencies == (
        "bom_intelligence",
    )


def test_planner_rejects_unregistered_selected_tool() -> None:
    registry = AgentToolRegistry(
        [
            PlannerTestTool(
                "component_intelligence",
                "Component intelligence.",
            )
        ]
    )

    planner = AgentPlanner(
        registry
    )

    with pytest.raises(
        ValueError,
        match=(
            "Planned tool 'bom_intelligence' "
            "is not registered"
        ),
    ):
        planner.plan(
            make_request(
                "Analyze the complete BOM"
            )
        )


def test_create_execution_plan_uses_registry_dependencies(
    registry: AgentToolRegistry,
) -> None:
    planner = AgentPlanner(
        registry
    )

    plan = planner.create_execution_plan(
        make_request(
            "Find alternatives for high-risk components"
        )
    )

    assert [
        step.tool_name
        for step in plan.steps
    ] == [
        "bom_intelligence",
        "alternative_analysis",
    ]

    assert plan.steps[0].dependencies == []
    assert plan.steps[1].dependencies == [
        "step_1"
    ]

def test_create_execution_plan_rejects_missing_dependency() -> None:
    registry = AgentToolRegistry(
        [
            PlannerTestTool(
                "alternative_analysis",
                "Alternative component analysis.",
                dependencies=(
                    "bom_intelligence",
                ),
            )
        ]
    )

    planner = AgentPlanner(
        registry
    )

    with pytest.raises(
        ValueError,
        match=(
            "Tool 'alternative_analysis' requires "
            "dependency 'bom_intelligence'"
        ),
    ):
        planner.create_execution_plan(
            make_request(
                "Find alternatives"
            )
        )