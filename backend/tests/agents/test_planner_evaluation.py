from dataclasses import dataclass

import pytest

from backend.app.agents.contracts import AgentRequest
from backend.app.agents.planner import AgentPlanner


@dataclass(frozen=True)
class PlannerEvaluationCase:
    """One deterministic planner evaluation scenario."""

    name: str
    task: str
    expected_tools: tuple[str, ...]


PLANNER_EVALUATION_CASES = (
    PlannerEvaluationCase(
        name="complete_bom_analysis",
        task="Analyze the complete BOM",
        expected_tools=(
            "bom_intelligence",
        ),
    ),
    PlannerEvaluationCase(
        name="bom_cost_analysis",
        task="Calculate the total BOM cost",
        expected_tools=(
            "bom_intelligence",
        ),
    ),
    PlannerEvaluationCase(
        name="bom_risk_analysis",
        task="Identify the overall BOM risk",
        expected_tools=(
            "bom_intelligence",
        ),
    ),
    PlannerEvaluationCase(
        name="component_availability",
        task="Check component availability",
        expected_tools=(
            "component_intelligence",
        ),
    ),
    PlannerEvaluationCase(
        name="supplier_pricing",
        task="Compare supplier quotes and pricing",
        expected_tools=(
            "component_intelligence",
        ),
    ),
    PlannerEvaluationCase(
        name="component_lifecycle",
        task="Check component lifecycle status",
        expected_tools=(
            "component_intelligence",
        ),
    ),
    PlannerEvaluationCase(
        name="alternative_analysis",
        task="Find alternatives for components",
        expected_tools=(
            "alternative_analysis",
        ),
    ),
    PlannerEvaluationCase(
        name="high_risk_alternatives",
        task="Find alternatives for high-risk components",
        expected_tools=(
            "bom_intelligence",
            "alternative_analysis",
        ),
    ),
    PlannerEvaluationCase(
        name="bom_based_replacements",
        task="Find replacements based on BOM risk",
        expected_tools=(
            "bom_intelligence",
            "alternative_analysis",
        ),
    ),
    PlannerEvaluationCase(
        name="generic_bom_request",
        task="Review this design",
        expected_tools=(
            "bom_intelligence",
        ),
    ),
)


@pytest.mark.parametrize(
    "case",
    PLANNER_EVALUATION_CASES,
    ids=lambda case: case.name,
)
def test_planner_selects_expected_tools(
    case: PlannerEvaluationCase,
) -> None:
    planner = AgentPlanner()

    request = AgentRequest(
        bom_id="BOM-EVAL-001",
        task=case.task,
        component_ids=["1"],
    )

    actual_tools = tuple(
        planner.plan(request)
    )

    assert actual_tools == case.expected_tools

def test_planner_evaluation_accuracy() -> None:
    planner = AgentPlanner()

    correct = 0

    for case in PLANNER_EVALUATION_CASES:
        request = AgentRequest(
            bom_id="BOM-EVAL-001",
            task=case.task,
            component_ids=["1"],
        )

        actual_tools = tuple(
            planner.plan(request)
        )

        if actual_tools == case.expected_tools:
            correct += 1

    total = len(
        PLANNER_EVALUATION_CASES
    )

    accuracy = correct / total

    assert accuracy == 1.0