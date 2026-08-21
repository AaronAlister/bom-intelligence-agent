import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from backend.app.agents.retry import RetryPolicy
from backend.app.agents.state import (
    AgentState,
    ExecutionPlan,
    ToolExecution,
    ToolResult,
)
from backend.app.agents.tools.base import AgentTool
from backend.app.agents.tools.registry import (
    AgentToolRegistry,
)

logger = logging.getLogger(__name__)


class AgentToolExecutor:
    """
    Executes tools selected by the planner.

    The executor is responsible for orchestration only.
    Business intelligence remains inside the existing
    deterministic intelligence services.

    Structured execution plans are preferred when available.
    Legacy planned tool lists remain supported for compatibility.
    """

    def __init__(
        self,
        tools: list[AgentTool],
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._registry = AgentToolRegistry(tools)
        self._retry_policy = (
            retry_policy
            if retry_policy is not None
            else RetryPolicy()
        )

    @property
    def tools(self) -> tuple[str, ...]:
        """Return the registered tool names."""
        return self._registry.names()

    @property
    def registry(self) -> AgentToolRegistry:
        """Return the tool registry used by the executor."""
        return self._registry

    async def execute(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Execute every tool planned for the current state.

        Structured execution plans are executed according to
        their dependency relationships. A step cannot execute
        until all of its dependencies have completed successfully.

        Legacy planned tool lists remain supported when no
        structured execution plan is present.
        """
        if getattr(state, "execution_plan", None) is not None:
            return await self._execute_plan(state)
        return await self._execute_legacy_plan(state)

    async def _execute_plan(
        self,
        state: AgentState,
    ) -> AgentState:
        """Execute a validated structured plan."""
        plan = state.execution_plan

        if plan is None or not plan.steps:
            state.status = "failed"
            state.errors.append(
                "Execution plan contains no steps."
            )
            return state

        validation_errors = self._validate_execution_plan(plan)

        if validation_errors:
            state.status = "failed"
            for error_message in validation_errors:
                state.errors.append(error_message)
            for step in plan.steps:
                step.status = "failed"
            return state

        state.status = "running"
        completed_steps: dict[str, str] = {}

        for step in plan.steps:
            dependency_failed = any(
                completed_steps.get(dependency) in {"failed", "skipped"}
                for dependency in step.dependencies
            )

            if dependency_failed:
                error_message = (
                    f"Step '{step.step_id}' was skipped "
                    "because a dependency failed."
                )
                execution = ToolExecution(
                    tool_name=step.tool_name,
                    status="skipped",
                    started_at=self._timestamp(),
                    completed_at=self._timestamp(),
                    error=error_message,
                )
                step.status = "skipped"
                state.executions.append(execution)
                state.errors.append(error_message)
                completed_steps[step.step_id] = "skipped"
                continue

            step_context = self._build_step_context(
                state,
                step.dependencies,
            )
            execution = await self._execute_tool(
                state,
                step.tool_name,
                step_context,
                step.step_id,
            )
            step.status = execution.status
            completed_steps[step.step_id] = execution.status

        self._finalize_plan_status(state)
        return state

    @staticmethod
    def _validate_execution_plan(
        plan: ExecutionPlan,
    ) -> list[str]:
        """
        Validate the complete execution graph before execution.

        Validation is performed before any tool is executed so
        malformed plans cannot cause partial execution.
        """
        errors: list[str] = []

        step_ids = [step.step_id for step in plan.steps]
        unique_step_ids = set(step_ids)

        if len(step_ids) != len(unique_step_ids):
            errors.append(
                "Execution plan contains duplicate step IDs."
            )

        known_step_ids = unique_step_ids

        for step in plan.steps:
            for dependency in step.dependencies:
                if dependency not in known_step_ids:
                    errors.append(
                        f"Step '{step.step_id}' references "
                        f"unknown dependency '{dependency}'."
                    )

        step_positions = {
            step.step_id: index
            for index, step in enumerate(plan.steps)
        }

        for step in plan.steps:
            current_position = step_positions[step.step_id]
            for dependency in step.dependencies:
                dependency_position = step_positions.get(dependency)
                if (
                    dependency_position is not None
                    and dependency_position >= current_position
                ):
                    errors.append(
                        f"Step '{step.step_id}' depends "
                        f"on '{dependency}', but the "
                        "dependency does not appear "
                        "before the step."
                    )

        if AgentToolExecutor._has_dependency_cycle(plan):
            errors.append(
                "Execution plan contains a dependency cycle."
            )

        return errors

    @staticmethod
    def _has_dependency_cycle(
        plan: ExecutionPlan,
    ) -> bool:
        """
        Return whether the execution plan contains a cycle.
        """
        dependencies = {
            step.step_id: set(step.dependencies)
            for step in plan.steps
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> bool:
            if step_id in visiting:
                return True
            if step_id in visited:
                return False

            visiting.add(step_id)
            for dependency in dependencies.get(step_id, set()):
                if visit(dependency):
                    return True
            visiting.remove(step_id)
            visited.add(step_id)
            return False

        return any(visit(step_id) for step_id in dependencies)

    @staticmethod
    def _dependencies_are_valid(
        dependencies: list[str],
        plan: ExecutionPlan,
        step_id: str,
    ) -> bool:
        """Validate that all dependencies reference earlier steps."""
        step_ids = [step.step_id for step in plan.steps]
        if step_id not in step_ids:
            return False
        current_index = step_ids.index(step_id)
        previous_step_ids = set(step_ids[:current_index])
        return all(
            dependency in previous_step_ids
            for dependency in dependencies
        )

    @staticmethod
    def _build_step_context(
        state: AgentState,
        dependencies: list[str],
    ) -> dict[str, Any]:
        """
        Build isolated context for a structured execution step.

        The context preserves the original agent context and
        exposes only outputs from declared dependencies.
        """
        context = dict(state.context)
        dependency_outputs: dict[str, dict[str, Any]] = {}
        for dependency in dependencies:
            output = state.step_outputs.get(dependency)
            if output is not None:
                dependency_outputs[dependency] = output
        context["step_outputs"] = dependency_outputs
        return context

    @staticmethod
    def _validate_tool_result(
        result: Any,
        expected_tool_name: str,
    ) -> str | None:
        """
        Validate the runtime result returned by a tool.

        Returns an error message when the result violates
        the AgentTool result contract. Returns None when
        the result is valid.
        """
        if not isinstance(result, ToolResult):
            return (
                f"Tool '{expected_tool_name}' returned an "
                f"invalid result type: "
                f"{type(result).__name__}."
            )

        if result.tool_name != expected_tool_name:
            return (
                f"Tool '{expected_tool_name}' returned a "
                f"result for '{result.tool_name}'."
            )

        if result.status not in {
            "success",
            "failed",
            "skipped",
        }:
            return (
                f"Tool '{expected_tool_name}' returned "
                f"an invalid status '{result.status}'."
            )

        return None

    async def _execute_tool(
        self,
        state: AgentState,
        tool_name: str,
        context: dict[str, Any] | None = None,
        step_id: str | None = None,
    ) -> ToolExecution:
        execution_context = state.context if context is None else context

        tool = (
            self._registry.get(tool_name)
            if self._registry.contains(tool_name)
            else None
        )

        execution = ToolExecution(
            tool_name=tool_name,
            status="pending",
            started_at=self._timestamp(),
        )
        execution.attempts = 0
        state.executions.append(execution)

        if tool is None:
            execution.status = "failed"
            execution.completed_at = self._timestamp()
            error_message = f"Tool '{tool_name}' is not registered."
            execution.error = error_message
            state.errors.append(error_message)
            return execution

        execution.status = "running"

        while True:
            execution.attempts += 1
            logger.info(
                "Agent tool execution started",
                extra={
                    "execution_id": getattr(state, "execution_id", "unknown"),
                    "bom_id": state.bom_id,
                    "tool_name": tool_name,
                    "attempt": execution.attempts,
                },
            )

            started = perf_counter()
            try:
                result = await tool.execute(
                    bom_id=state.bom_id,
                    component_ids=state.component_ids,
                    context=execution_context,
                )

                elapsed_ms = (perf_counter() - started) * 1000

                # Validate result contract before mutating state
                validation_error = self._validate_tool_result(
                    result,
                    tool_name,
                )

                if validation_error is not None:
                    execution.execution_time_ms = elapsed_ms
                    execution.status = "failed"
                    execution.error = validation_error
                    execution.completed_at = self._timestamp()

                    state.errors.append(validation_error)

                    logger.error(
                        "Agent tool returned an invalid result",
                        extra={
                            "execution_id": getattr(state, "execution_id", "unknown"),
                            "bom_id": state.bom_id,
                            "tool_name": tool_name,
                            "error": validation_error,
                        },
                    )

                    return execution

                # Valid result: proceed with state mutation
                result.execution_time_ms = elapsed_ms
                state.tool_results.append(result)

                if step_id is not None and result.status == "success":
                    state.step_outputs[step_id] = result.data

                execution.execution_time_ms = elapsed_ms
                execution.completed_at = self._timestamp()

                if result.status == "success":
                    execution.status = "success"
                elif result.status == "skipped":
                    execution.status = "skipped"
                else:
                    execution.status = "failed"
                    if result.error:
                        execution.error = result.error
                        state.errors.append(result.error)

                state.evidence.extend(result.evidence)

                logger.info(
                    "Agent tool execution completed",
                    extra={
                        "execution_id": getattr(state, "execution_id", "unknown"),
                        "bom_id": state.bom_id,
                        "tool_name": tool_name,
                        "status": execution.status,
                        "attempts": execution.attempts,
                        "execution_time_ms": execution.execution_time_ms,
                    },
                )

                return execution

            except Exception as exc:
                elapsed_ms = (perf_counter() - started) * 1000
                execution.execution_time_ms = elapsed_ms
                execution.error = str(exc)

                classification = self._retry_policy.classify(exc)

                if self._retry_policy.should_retry(exc, execution.attempts):
                    logger.warning(
                        "Retrying agent tool execution",
                        extra={
                            "execution_id": getattr(state, "execution_id", "unknown"),
                            "bom_id": state.bom_id,
                            "tool_name": tool_name,
                            "attempt": execution.attempts,
                            "max_attempts": self._retry_policy.max_attempts,
                            "classification": classification.value,
                            "error": str(exc),
                        },
                    )
                    continue

                execution.status = "failed"
                execution.completed_at = self._timestamp()
                state.errors.append(f"Tool '{tool_name}' failed: {exc}")

                logger.exception(
                    "Agent tool execution raised a non-retryable exception",
                    extra={
                        "execution_id": getattr(state, "execution_id", "unknown"),
                        "bom_id": state.bom_id,
                        "tool_name": tool_name,
                        "attempts": execution.attempts,
                        "classification": classification.value,
                    },
                )
                return execution

    async def _execute_legacy_plan(
        self,
        state: AgentState,
    ) -> AgentState:
        """Execute the legacy flat tool list."""
        if not state.planned_tools:
            state.status = "failed"
            state.errors.append(
                "No tools were planned for execution."
            )
            return state

        state.status = "running"
        for tool_name in state.planned_tools:
            await self._execute_tool(state, tool_name)

        self._finalize_status(state)
        return state

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _finalize_status(state: AgentState) -> None:
        executions = state.executions
        if not executions:
            state.status = "failed"
            return

        successful = sum(1 for e in executions if e.status == "success")
        failed = sum(1 for e in executions if e.status == "failed")
        skipped = sum(1 for e in executions if e.status == "skipped")

        if successful == len(executions):
            state.status = "success"
        elif successful > 0:
            state.status = "partial"
        elif skipped == len(executions):
            state.status = "partial"
        elif failed == len(executions):
            state.status = "failed"
        else:
            state.status = "partial"

    @staticmethod
    def _finalize_plan_status(
        state: AgentState,
        *,
        plan_invalid: bool = False,
    ) -> None:
        """Finalize state status for structured plan execution."""
        if not state.executions:
            state.status = "failed"
            return

        if plan_invalid:
            state.status = "failed"
            return

        statuses = {e.status for e in state.executions}
        if "failed" in statuses:
            if "success" in statuses or "skipped" in statuses:
                state.status = "partial"
            else:
                state.status = "failed"
            return

        if "skipped" in statuses:
            if "success" in statuses:
                state.status = "partial"
            else:
                state.status = "failed"
            return

        state.status = "success"