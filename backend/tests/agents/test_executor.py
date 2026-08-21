from typing import Any, cast

import pytest

from backend.app.agents.executor import (
    AgentToolExecutor,
)
from backend.app.agents.retry import RetryClassification, RetryPolicy
from backend.app.agents.state import (
    AgentState,
    ExecutionPlan,
    PlanStep,
    ToolResult,
)
from backend.app.agents.tools.base import (
    AgentTool,
)


class SuccessfulTool(AgentTool):
    name = "successful"
    description = "Always succeeds."

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
            },
        )


class FailingTool(AgentTool):
    name = "failing"
    description = "Always fails."

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            status="failed",
            error="Intentional test failure.",
        )


class RaisingTool(AgentTool):
    name = "raising"
    description = "Raises an exception."

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        raise RuntimeError(
            "Unexpected tool failure."
        )


class RecordingTool(AgentTool):
    """Records execution order and returns evidence."""

    def __init__(
        self,
        name: str,
        execution_log: list[str],
    ) -> None:
        self.name = name
        self.description = f"Recording tool: {name}"
        self._execution_log = execution_log

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        self._execution_log.append(self.name)
        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "tool": self.name,
            },
        )


class ContextRecordingTool(AgentTool):
    """Records the context received during execution."""

    def __init__(
        self,
        name: str,
        received_contexts: list[dict[str, Any]],
    ) -> None:
        self.name = name
        self.description = (
            f"Context recording tool: {name}"
        )
        self._received_contexts = received_contexts

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        self._received_contexts.append(
            context
        )

        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "producer": self.name,
                "value": "generated-data",
            },
        )


@pytest.mark.asyncio
async def test_executor_runs_registered_tool():
    executor = AgentToolExecutor(
        [SuccessfulTool()]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Analyze BOM",
        planned_tools=["successful"],
    )

    result = await executor.execute(state)

    assert result.status == "success"
    assert len(result.tool_results) == 1

    assert (
        result.tool_results[0].tool_name
        == "successful"
    )

    assert len(result.executions) == 1

    execution = result.executions[0]

    assert execution.tool_name == "successful"
    assert execution.status == "success"
    assert execution.completed_at is not None
    assert execution.execution_time_ms is not None


@pytest.mark.asyncio
async def test_executor_handles_tool_failure():
    executor = AgentToolExecutor(
        [FailingTool()]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Analyze risk",
        planned_tools=["failing"],
    )

    result = await executor.execute(state)

    assert result.status == "failed"

    assert len(result.tool_results) == 1

    assert (
        result.tool_results[0].status
        == "failed"
    )

    assert result.errors == [
        "Intentional test failure."
    ]

    assert (
        result.executions[0].status
        == "failed"
    )


@pytest.mark.asyncio
async def test_executor_isolates_unexpected_exception():
    executor = AgentToolExecutor(
        [RaisingTool()]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Analyze risk",
        planned_tools=["raising"],
    )

    result = await executor.execute(state)

    assert result.status == "failed"

    assert len(result.errors) == 1

    assert (
        "Unexpected tool failure."
        in result.errors[0]
    )

    assert (
        result.executions[0].status
        == "failed"
    )


@pytest.mark.asyncio
async def test_executor_produces_partial_result():
    executor = AgentToolExecutor(
        [
            SuccessfulTool(),
            FailingTool(),
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Analyze BOM and alternatives",
        planned_tools=[
            "successful",
            "failing",
        ],
    )

    result = await executor.execute(state)

    assert result.status == "partial"

    assert len(result.tool_results) == 2

    assert (
        result.executions[0].status
        == "success"
    )

    assert (
        result.executions[1].status
        == "failed"
    )


@pytest.mark.asyncio
async def test_executor_handles_unknown_tool():
    executor = AgentToolExecutor([])

    state = AgentState(
        bom_id="BOM-001",
        task="Analyze BOM",
        planned_tools=["unknown"],
    )

    result = await executor.execute(state)

    assert result.status == "failed"

    assert len(result.errors) == 1

    assert (
        "not registered"
        in result.errors[0]
    )

    assert (
        result.executions[0].status
        == "failed"
    )


@pytest.mark.asyncio
async def test_executor_rejects_empty_plan():
    executor = AgentToolExecutor(
        [SuccessfulTool()]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Analyze BOM",
    )

    result = await executor.execute(state)

    assert result.status == "failed"

    assert result.errors == [
        "No tools were planned for execution."
    ]


def test_executor_exposes_registered_tools():
    executor = AgentToolExecutor(
        [
            SuccessfulTool(),
            FailingTool(),
        ]
    )

    assert executor.tools == (
        "successful",
        "failing",
    )


@pytest.mark.asyncio
async def test_executor_preserves_planned_tool_order():
    execution_log: list[str] = []
    executor = AgentToolExecutor(
        [
            RecordingTool(
                "first",
                execution_log,
            ),
            RecordingTool(
                "second",
                execution_log,
            ),
            RecordingTool(
                "third",
                execution_log,
            ),
        ]
    )
    state = AgentState(
        bom_id="BOM-001",
        task="Run multiple capabilities",
        planned_tools=[
            "first",
            "second",
            "third",
        ],
    )
    result = await executor.execute(state)
    assert result.status == "success"
    assert execution_log == [
        "first",
        "second",
        "third",
    ]
    assert [
        execution.tool_name
        for execution in result.executions
    ] == [
        "first",
        "second",
        "third",
    ]
    assert [
        tool_result.tool_name
        for tool_result in result.tool_results
    ] == [
        "first",
        "second",
        "third",
    ]


@pytest.mark.asyncio
async def test_executor_continues_after_failed_tool():
    execution_log: list[str] = []

    class RecordingFailureTool(AgentTool):
        name = "failure"
        description = "Fails while recording execution."

        async def execute(
            self,
            *,
            bom_id: str,
            component_ids: list[str],
            context: dict[str, Any],
        ) -> ToolResult:
            execution_log.append(self.name)
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error="Expected failure.",
            )

    executor = AgentToolExecutor(
        [
            RecordingTool(
                "first",
                execution_log,
            ),
            RecordingFailureTool(),
            RecordingTool(
                "third",
                execution_log,
            ),
        ]
    )
    state = AgentState(
        bom_id="BOM-001",
        task="Run multiple capabilities",
        planned_tools=[
            "first",
            "failure",
            "third",
        ],
    )
    result = await executor.execute(state)
    assert result.status == "partial"
    assert execution_log == [
        "first",
        "failure",
        "third",
    ]
    assert [
        execution.status
        for execution in result.executions
    ] == [
        "success",
        "failed",
        "success",
    ]
    assert [
        execution.tool_name
        for execution in result.executions
    ] == [
        "first",
        "failure",
        "third",
    ]


@pytest.mark.asyncio
async def test_executor_respects_successful_dependency() -> None:
    execution_log: list[str] = []

    first_tool = RecordingTool(
        "first",
        execution_log,
    )

    second_tool = RecordingTool(
        "second",
        execution_log,
    )

    executor = AgentToolExecutor(
        [
            first_tool,
            second_tool,
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Run dependent capabilities",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="first",
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="second",
                    dependencies=["step_1"],
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "success"

    assert execution_log == [
        "first",
        "second",
    ]

    assert [
        execution.tool_name
        for execution in result.executions
    ] == [
        "first",
        "second",
    ]

    assert [
        execution.status
        for execution in result.executions
    ] == [
        "success",
        "success",
    ]


@pytest.mark.asyncio
async def test_executor_skips_step_when_dependency_fails() -> None:
    execution_log: list[str] = []

    class RecordingFailureTool(AgentTool):
        name = "failure"
        description = "Fails while recording execution."

        async def execute(
            self,
            *,
            bom_id: str,
            component_ids: list[str],
            context: dict[str, Any],
        ) -> ToolResult:
            execution_log.append(self.name)

            return ToolResult(
                tool_name=self.name,
                status="failed",
                error="Dependency failure.",
            )

    dependent_tool = RecordingTool(
        "dependent",
        execution_log,
    )

    executor = AgentToolExecutor(
        [
            RecordingFailureTool(),
            dependent_tool,
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Run dependent capabilities",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="failure",
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="dependent",
                    dependencies=["step_1"],
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "partial"

    assert execution_log == [
        "failure",
    ]

    assert [
        execution.tool_name
        for execution in result.executions
    ] == [
        "failure",
        "dependent",
    ]

    assert [
        execution.status
        for execution in result.executions
    ] == [
        "failed",
        "skipped",
    ]

    assert result.execution_plan is not None

    assert result.execution_plan.steps[0].status == (
        "failed"
    )

    assert result.execution_plan.steps[1].status == (
        "skipped"
    )


@pytest.mark.asyncio
async def test_executor_rejects_invalid_dependency() -> None:
    execution_log: list[str] = []

    executor = AgentToolExecutor(
        [
            RecordingTool(
                "first",
                execution_log,
            ),
            RecordingTool(
                "second",
                execution_log,
            ),
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Run invalid dependency",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="first",
                    dependencies=["step_2"],
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="second",
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    # Now we reject the plan before any execution
    assert result.status == "failed"
    assert execution_log == []

    execution_plan = result.execution_plan
    assert execution_plan is not None
    assert execution_plan.steps[0].status == "failed"
    assert execution_plan.steps[1].status == "failed"

    assert any(
        "dependency" in error
        for error in result.errors
    )


@pytest.mark.asyncio
async def test_executor_runs_independent_plan_steps() -> None:
    execution_log: list[str] = []

    executor = AgentToolExecutor(
        [
            RecordingTool(
                "first",
                execution_log,
            ),
            RecordingTool(
                "second",
                execution_log,
            ),
            RecordingTool(
                "third",
                execution_log,
            ),
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Run independent capabilities",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="first",
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="second",
                ),
                PlanStep(
                    step_id="step_3",
                    tool_name="third",
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "success"

    assert execution_log == [
        "first",
        "second",
        "third",
    ]

    execution_plan = result.execution_plan

    assert execution_plan is not None

    assert [
        step.status
        for step in execution_plan.steps
    ] == [
        "success",
        "success",
        "success",
    ]


@pytest.mark.asyncio
async def test_executor_passes_dependency_output_to_next_step() -> None:
    received_contexts: list[
        dict[str, Any]
    ] = []

    first_tool = ContextRecordingTool(
        "first",
        received_contexts,
    )

    second_tool = ContextRecordingTool(
        "second",
        received_contexts,
    )

    executor = AgentToolExecutor(
        [
            first_tool,
            second_tool,
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Pass data between steps",
        context={
            "components": [
                {
                    "component_id": "C-001",
                    "mpn": "TEST-MPN",
                }
            ]
        },
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="first",
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="second",
                    dependencies=["step_1"],
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "success"

    assert len(received_contexts) == 2

    assert received_contexts[0]["components"] == [
        {
            "component_id": "C-001",
            "mpn": "TEST-MPN",
        }
    ]

    assert received_contexts[0]["step_outputs"] == {}

    assert received_contexts[1]["step_outputs"] == {
        "step_1": {
            "producer": "first",
            "value": "generated-data",
        }
    }


@pytest.mark.asyncio
async def test_executor_does_not_propagate_failed_output() -> None:
    received_contexts: list[
        dict[str, Any]
    ] = []

    class FailingContextTool(AgentTool):
        name = "failing_context"
        description = "Fails without producing output."

        async def execute(
            self,
            *,
            bom_id: str,
            component_ids: list[str],
            context: dict[str, Any],
        ) -> ToolResult:
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error="Upstream failure.",
            )

    dependent_tool = ContextRecordingTool(
        "dependent",
        received_contexts,
    )

    executor = AgentToolExecutor(
        [
            FailingContextTool(),
            dependent_tool,
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Do not propagate failed output",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="failing_context",
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="dependent",
                    dependencies=["step_1"],
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "partial"

    assert received_contexts == []

    assert result.step_outputs == {}


@pytest.mark.asyncio
async def test_executor_scopes_context_to_declared_dependencies() -> None:
    received_contexts: list[
        dict[str, Any]
    ] = []

    first_tool = ContextRecordingTool(
        "first",
        received_contexts,
    )

    second_tool = ContextRecordingTool(
        "second",
        received_contexts,
    )

    third_tool = ContextRecordingTool(
        "third",
        received_contexts,
    )

    executor = AgentToolExecutor(
        [
            first_tool,
            second_tool,
            third_tool,
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Scope dependency outputs",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="first",
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="second",
                ),
                PlanStep(
                    step_id="step_3",
                    tool_name="third",
                    dependencies=["step_1"],
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "success"

    assert received_contexts[2]["step_outputs"] == {
        "step_1": {
            "producer": "first",
            "value": "generated-data",
        }
    }


# ----- Retry integration tests -----

class RetryableTool(AgentTool):
    """Fails transiently before succeeding."""

    name = "retryable"
    description = "Fails with TimeoutError once."

    def __init__(self) -> None:
        self.attempts = 0

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        self.attempts += 1
        if self.attempts == 1:
            raise TimeoutError("Temporary timeout.")
        return ToolResult(
            tool_name=self.name,
            status="success",
            data={"attempts": self.attempts},
        )


@pytest.mark.asyncio
async def test_executor_retries_transient_exception() -> None:
    tool = RetryableTool()
    executor = AgentToolExecutor(
        [tool],
        retry_policy=RetryPolicy(max_attempts=2),
    )
    state = AgentState(
        bom_id="BOM-001",
        task="Retry transient failure",
        planned_tools=["retryable"],
    )
    result = await executor.execute(state)

    assert result.status == "success"
    assert tool.attempts == 2
    assert len(result.executions) == 1
    execution = result.executions[0]
    assert execution.status == "success"
    assert execution.attempts == 2


class AlwaysTimeoutTool(AgentTool):
    """Always raises a retryable timeout."""

    name = "always_timeout"
    description = "Always raises TimeoutError."

    def __init__(self) -> None:
        self.attempts = 0

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        self.attempts += 1
        raise TimeoutError("Persistent timeout.")


@pytest.mark.asyncio
async def test_executor_stops_after_retry_limit() -> None:
    tool = AlwaysTimeoutTool()
    executor = AgentToolExecutor(
        [tool],
        retry_policy=RetryPolicy(max_attempts=2),
    )
    state = AgentState(
        bom_id="BOM-001",
        task="Exhaust retries",
        planned_tools=["always_timeout"],
    )
    result = await executor.execute(state)

    assert result.status == "failed"
    assert tool.attempts == 2
    assert len(result.executions) == 1
    execution = result.executions[0]
    assert execution.status == "failed"
    assert execution.attempts == 2
    assert any("Persistent timeout." in error for error in result.errors)


@pytest.mark.asyncio
async def test_executor_does_not_retry_tool_result_failure() -> None:
    tool = FailingTool()
    executor = AgentToolExecutor(
        [tool],
        retry_policy=RetryPolicy(max_attempts=3),
    )
    state = AgentState(
        bom_id="BOM-001",
        task="Do not retry deterministic failure",
        planned_tools=["failing"],
    )
    result = await executor.execute(state)

    assert result.status == "failed"
    assert len(result.executions) == 1
    execution = result.executions[0]
    assert execution.status == "failed"
    assert execution.attempts == 1


# ----- Plan validation guardrail tests -----

@pytest.mark.asyncio
async def test_executor_rejects_duplicate_step_ids() -> None:
    execution_log: list[str] = []

    executor = AgentToolExecutor(
        [
            RecordingTool(
                "first",
                execution_log,
            ),
            RecordingTool(
                "second",
                execution_log,
            ),
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Run duplicate steps",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="first",
                ),
                PlanStep(
                    step_id="step_1",
                    tool_name="second",
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "failed"
    assert execution_log == []
    assert any(
        "duplicate step IDs" in error
        for error in result.errors
    )


@pytest.mark.asyncio
async def test_executor_rejects_unknown_dependency() -> None:
    execution_log: list[str] = []

    executor = AgentToolExecutor(
        [
            RecordingTool(
                "first",
                execution_log,
            ),
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Run unknown dependency",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="first",
                    dependencies=["missing_step"],
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "failed"
    assert execution_log == []
    assert any(
        "unknown dependency" in error
        for error in result.errors
    )


@pytest.mark.asyncio
async def test_executor_rejects_dependency_cycle() -> None:
    execution_log: list[str] = []

    executor = AgentToolExecutor(
        [
            RecordingTool(
                "first",
                execution_log,
            ),
            RecordingTool(
                "second",
                execution_log,
            ),
        ]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Run cyclic dependencies",
        execution_plan=ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="first",
                    dependencies=["step_2"],
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="second",
                    dependencies=["step_1"],
                ),
            ]
        ),
    )

    result = await executor.execute(state)

    assert result.status == "failed"
    assert execution_log == []
    assert any(
        "dependency cycle" in error
        for error in result.errors
    )


# ----- Tool result contract validation tests -----

class WrongToolResultTool(AgentTool):
    """Returns a result belonging to another tool."""

    name = "wrong_result"
    description = "Returns a mismatched tool result."

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        return ToolResult(
            tool_name="different_tool",
            status="success",
            data={
                "unexpected": True,
            },
        )


@pytest.mark.asyncio
async def test_executor_rejects_mismatched_tool_result() -> None:
    executor = AgentToolExecutor(
        [WrongToolResultTool()]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Validate tool result",
        planned_tools=["wrong_result"],
    )

    result = await executor.execute(state)

    assert result.status == "failed"
    assert len(result.tool_results) == 0
    assert len(result.executions) == 1

    execution = result.executions[0]
    assert execution.status == "failed"
    assert execution.error is not None
    assert (
        "returned a result for 'different_tool'"
        in execution.error
    )
    assert result.step_outputs == {}


class InvalidResultTypeTool(AgentTool):
    """Returns a value violating the ToolResult contract."""

    name = "invalid_result_type"
    description = "Returns an invalid result type."

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        invalid_result: Any = {
            "tool_name": self.name,
            "status": "success",
        }
        return cast(
            ToolResult,
            invalid_result,
        )


@pytest.mark.asyncio
async def test_executor_rejects_invalid_result_type() -> None:
    executor = AgentToolExecutor(
        [InvalidResultTypeTool()]
    )

    state = AgentState(
        bom_id="BOM-001",
        task="Validate result type",
        planned_tools=["invalid_result_type"],
    )

    result = await executor.execute(state)

    assert result.status == "failed"
    assert result.tool_results == []
    assert len(result.executions) == 1

    execution = result.executions[0]
    assert execution.status == "failed"
    assert execution.error is not None
    assert (
        "invalid result type"
        in execution.error
    )