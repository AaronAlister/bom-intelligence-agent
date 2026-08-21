from backend.app.agents.contracts import Evidence
from backend.app.agents.state import (
    AgentState,
    ExecutionPlan,
    PlanStep,
    ToolExecution,
    ToolResult,
)


def test_agent_state_defaults():
    state = AgentState(
        bom_id="BOM-001",
        task="Analyze procurement risk",
    )

    assert state.bom_id == "BOM-001"
    assert state.task == "Analyze procurement risk"

    assert state.planned_tools == []
    assert state.executions == []
    assert state.tool_results == []
    assert state.findings == []
    assert state.risks == []
    assert state.recommendations == []
    assert state.evidence == []
    assert state.errors == []

    assert state.status == "pending"


def test_tool_result_supports_evidence():
    evidence = Evidence(
        source="supplier_api",
        source_id="quote-001",
        excerpt="Available quantity: 500",
    )

    result = ToolResult(
        tool_name="supplier",
        status="success",
        data={
            "supplier": "Example Supplier",
            "quantity_available": 500,
        },
        evidence=[evidence],
    )

    assert result.tool_name == "supplier"
    assert result.status == "success"
    assert result.data["quantity_available"] == 500
    assert len(result.evidence) == 1


def test_tool_execution_tracks_runtime():
    execution = ToolExecution(
        tool_name="bom_risk",
        status="success",
        execution_time_ms=42.5,
    )

    assert execution.tool_name == "bom_risk"
    assert execution.status == "success"
    assert execution.execution_time_ms == 42.5


def test_agent_state_can_track_execution():
    state = AgentState(
        bom_id="BOM-002",
        task="Find high-risk components",
        planned_tools=["bom_risk"],
        executions=[
            ToolExecution(
                tool_name="bom_risk",
                status="success",
                execution_time_ms=18.2,
            )
        ],
        tool_results=[
            ToolResult(
                tool_name="bom_risk",
                status="success",
                data={
                    "risk_level": "HIGH"
                },
            )
        ],
    )

    assert state.planned_tools == ["bom_risk"]
    assert len(state.executions) == 1
    assert len(state.tool_results) == 1
    assert state.tool_results[0].data["risk_level"] == "HIGH"


def test_plan_step_defaults() -> None:
    step = PlanStep(
        step_id="step_1",
        tool_name="bom_intelligence",
    )

    assert step.step_id == "step_1"
    assert step.tool_name == "bom_intelligence"
    assert step.dependencies == []
    assert step.status == "pending"
    assert step.metadata == {}


def test_execution_plan_defaults() -> None:
    plan = ExecutionPlan()

    assert plan.steps == []
    assert plan.metadata == {}


def test_execution_plan_contains_structured_steps() -> None:
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                tool_name="bom_intelligence",
            ),
            PlanStep(
                step_id="step_2",
                tool_name="alternative_analysis",
                dependencies=["step_1"],
            ),
        ]
    )

    assert len(plan.steps) == 2
    assert plan.steps[0].tool_name == (
        "bom_intelligence"
    )
    assert plan.steps[1].tool_name == (
        "alternative_analysis"
    )
    assert plan.steps[1].dependencies == [
        "step_1"
    ]