from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.app.agents.contracts import Evidence


ToolStatus = Literal[
    "pending",
    "running",
    "success",
    "failed",
    "skipped",
]


class PlanStep(BaseModel):
    """One step in a structured agent execution plan."""

    step_id: str
    tool_name: str

    dependencies: list[str] = Field(
        default_factory=list
    )

    status: ToolStatus = "pending"

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class ExecutionPlan(BaseModel):
    """Structured execution plan produced by the agent planner."""

    steps: list[PlanStep] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class ToolResult(BaseModel):
    """Standard result returned by an agent tool."""

    tool_name: str
    status: Literal["success", "failed", "skipped"]

    data: dict[str, Any] = Field(
        default_factory=dict
    )

    evidence: list[Evidence] = Field(
        default_factory=list
    )

    error: str | None = None

    execution_time_ms: float | None = None


class ToolExecution(BaseModel):
    """Execution metadata for one planned tool."""

    tool_name: str

    status: ToolStatus = "pending"

    attempts: int = 0

    started_at: str | None = None
    completed_at: str | None = None

    execution_time_ms: float | None = None

    error: str | None = None


class AgentState(BaseModel):
    """
    Mutable state carried through the BOM agent workflow.

    The state records both intelligence results and
    orchestration metadata so execution remains observable.
    """

    bom_id: str

    execution_plan: ExecutionPlan | None = None

    task: str

    context: dict[str, Any] = Field(
        default_factory=dict
    )

    component_ids: list[str] = Field(
        default_factory=list
    )

    requested_evidence: list[str] = Field(
        default_factory=list
    )

    planned_tools: list[str] = Field(
        default_factory=list
    )

    executions: list[ToolExecution] = Field(
        default_factory=list
    )

    tool_results: list[ToolResult] = Field(
        default_factory=list
    )

    step_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )

    findings: list[dict[str, Any]] = Field(
        default_factory=list
    )

    risks: list[dict[str, Any]] = Field(
        default_factory=list
    )

    recommendations: list[dict[str, Any]] = Field(
        default_factory=list
    )

    evidence: list[Evidence] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )

    status: Literal[
        "pending",
        "running",
        "success",
        "partial",
        "failed",
    ] = "pending"

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    execution_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    started_at: str | None = None

    completed_at: str | None = None

    execution_time_ms: float | None = None