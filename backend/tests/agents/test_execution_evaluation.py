from dataclasses import dataclass
from statistics import mean, median
from time import perf_counter
from typing import Any

import pytest

from backend.app.agents.executor import (
    AgentToolExecutor,
)
from backend.app.agents.retry import (
    RetryPolicy,
)
from backend.app.agents.state import (
    AgentState,
    ToolResult,
)
from backend.app.agents.tools.base import (
    AgentTool,
)


@dataclass(frozen=True)
class ExecutionEvaluationCase:
    """One controlled executor reliability scenario."""

    name: str
    expected_status: str


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
                "result": "success",
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
            error="Expected failure.",
        )


class RetryableTool(AgentTool):
    name = "retryable"
    description = "Fails once and then succeeds."

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
            raise TimeoutError(
                "Temporary failure."
            )

        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "result": "recovered",
            },
        )


class AlwaysTimeoutTool(AgentTool):
    name = "always_timeout"
    description = "Always raises a timeout."

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        raise TimeoutError(
            "Persistent timeout."
        )


def _percentile(
    values: list[float],
    percentile: float,
) -> float:
    """
    Calculate a percentile using linear interpolation.

    The input list must contain at least one value.
    """

    if not values:
        raise ValueError(
            "Cannot calculate a percentile "
            "from an empty sequence."
        )

    if not 0.0 <= percentile <= 100.0:
        raise ValueError(
            "Percentile must be between 0 and 100."
        )

    ordered = sorted(values)

    position = (
        (len(ordered) - 1)
        * percentile
        / 100.0
    )

    lower_index = int(position)
    upper_index = min(
        lower_index + 1,
        len(ordered) - 1,
    )

    weight = position - lower_index

    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]

    return (
        lower_value
        + (upper_value - lower_value)
        * weight
    )


def _build_successful_execution() -> (
    tuple[AgentToolExecutor, AgentState]
):
    """Build one deterministic successful execution."""

    executor = AgentToolExecutor(
        [SuccessfulTool()]
    )

    state = AgentState(
        bom_id="BOM-EVAL-001",
        task="latency_baseline",
        planned_tools=["successful"],
    )

    return executor, state


@pytest.mark.asyncio
async def test_execution_evaluation_matrix() -> None:
    cases = (
        ExecutionEvaluationCase(
            name="normal_success",
            expected_status="success",
        ),
        ExecutionEvaluationCase(
            name="tool_failure",
            expected_status="failed",
        ),
        ExecutionEvaluationCase(
            name="partial_execution",
            expected_status="partial",
        ),
        ExecutionEvaluationCase(
            name="retry_recovery",
            expected_status="success",
        ),
        ExecutionEvaluationCase(
            name="retry_exhaustion",
            expected_status="failed",
        ),
    )

    results: list[tuple[str, str]] = []

    for case in cases:
        if case.name == "normal_success":
            executor = AgentToolExecutor(
                [SuccessfulTool()]
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=["successful"],
            )

        elif case.name == "tool_failure":
            executor = AgentToolExecutor(
                [FailingTool()]
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=["failing"],
            )

        elif case.name == "partial_execution":
            executor = AgentToolExecutor(
                [
                    SuccessfulTool(),
                    FailingTool(),
                ]
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=[
                    "successful",
                    "failing",
                ],
            )

        elif case.name == "retry_recovery":
            tool = RetryableTool()

            executor = AgentToolExecutor(
                [tool],
                retry_policy=RetryPolicy(
                    max_attempts=2,
                ),
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=["retryable"],
            )

        else:
            executor = AgentToolExecutor(
                [AlwaysTimeoutTool()],
                retry_policy=RetryPolicy(
                    max_attempts=2,
                ),
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=[
                    "always_timeout",
                ],
            )

        result = await executor.execute(
            state
        )

        results.append(
            (
                case.name,
                result.status,
            )
        )

        assert result.status == (
            case.expected_status
        )

    assert len(results) == len(cases)


@pytest.mark.asyncio
async def test_execution_reliability_score() -> None:
    cases = (
        ExecutionEvaluationCase(
            name="normal_success",
            expected_status="success",
        ),
        ExecutionEvaluationCase(
            name="tool_failure",
            expected_status="failed",
        ),
        ExecutionEvaluationCase(
            name="partial_execution",
            expected_status="partial",
        ),
        ExecutionEvaluationCase(
            name="retry_recovery",
            expected_status="success",
        ),
        ExecutionEvaluationCase(
            name="retry_exhaustion",
            expected_status="failed",
        ),
    )

    correct = 0

    for case in cases:
        if case.name == "normal_success":
            executor = AgentToolExecutor(
                [SuccessfulTool()]
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=["successful"],
            )

        elif case.name == "tool_failure":
            executor = AgentToolExecutor(
                [FailingTool()]
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=["failing"],
            )

        elif case.name == "partial_execution":
            executor = AgentToolExecutor(
                [
                    SuccessfulTool(),
                    FailingTool(),
                ]
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=[
                    "successful",
                    "failing",
                ],
            )

        elif case.name == "retry_recovery":
            executor = AgentToolExecutor(
                [RetryableTool()],
                retry_policy=RetryPolicy(
                    max_attempts=2,
                ),
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=["retryable"],
            )

        else:
            executor = AgentToolExecutor(
                [AlwaysTimeoutTool()],
                retry_policy=RetryPolicy(
                    max_attempts=2,
                ),
            )

            state = AgentState(
                bom_id="BOM-EVAL-001",
                task=case.name,
                planned_tools=[
                    "always_timeout",
                ],
            )

        result = await executor.execute(
            state
        )

        if result.status == case.expected_status:
            correct += 1

    total = len(cases)
    reliability = correct / total

    assert reliability == 1.0


@pytest.mark.asyncio
async def test_execution_latency_baseline() -> None:
    """
    Establish a deterministic executor latency baseline.

    This is a local orchestration benchmark. It is not a
    production SLA or external-service performance benchmark.
    """

    warmup_runs = 3
    measured_runs = 30

    for _ in range(warmup_runs):
        executor, state = (
            _build_successful_execution()
        )

        result = await executor.execute(
            state
        )

        assert result.status == "success"

    latencies_ms: list[float] = []

    for _ in range(measured_runs):
        executor, state = (
            _build_successful_execution()
        )

        started = perf_counter()

        result = await executor.execute(
            state
        )

        elapsed_ms = (
            perf_counter() - started
        ) * 1000.0

        assert result.status == "success"

        latencies_ms.append(
            elapsed_ms
        )

    average_ms = mean(latencies_ms)
    median_ms = median(latencies_ms)
    p95_ms = _percentile(
        latencies_ms,
        95.0,
    )

    print(
        "\nExecution latency baseline:"
        f"\n  runs: {measured_runs}"
        f"\n  mean: {average_ms:.3f} ms"
        f"\n  median: {median_ms:.3f} ms"
        f"\n  p95: {p95_ms:.3f} ms"
    )

    assert len(latencies_ms) == (
        measured_runs
    )

    assert all(
        latency >= 0.0
        for latency in latencies_ms
    )