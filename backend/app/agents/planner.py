from backend.app.agents.contracts import AgentRequest
from backend.app.agents.state import (
    ExecutionPlan,
    PlanStep,
)
from backend.app.agents.tools.registry import (
    AgentToolRegistry,
    ToolMetadata,
)


class AgentPlanner:
    """
    Deterministic planner for BOM intelligence tasks.

    The planner selects which existing agent capabilities
    are required for a request. It does not execute tools
    and does not perform intelligence calculations.
    """

    COMPONENT_TOOL = "component_intelligence"
    BOM_TOOL = "bom_intelligence"
    ALTERNATIVE_TOOL = "alternative_analysis"

    def __init__(
        self,
        registry: AgentToolRegistry | None = None,
        *,
        validate_registered_tools: bool = True,
    ) -> None:
        self._registry = registry
        self._validate_registered_tools = (
            validate_registered_tools
        )

    def set_registry(
        self,
        registry: AgentToolRegistry,
    ) -> None:
        """
        Bind the planner to the runtime tool registry.

        The executor owns the runtime registry, while the
        planner consumes it for capability-aware planning.
        """
        self._registry = registry

    def plan(
        self,
        request: AgentRequest,
    ) -> list[str]:
        """
        Select the tools required to satisfy a request.

        Planning is deterministic so that tool selection
        remains predictable and testable before introducing
        an LLM-based planner.
        """
        task = request.task.strip().lower()

        if not task:
            raise ValueError(
                "Agent task cannot be empty"
            )

        tools: list[str] = []

        alternative_requested = any(
            keyword in task
            for keyword in (
                "alternative",
                "alternatives",
                "replacement",
                "replacements",
                "substitute",
                "substitutes",
            )
        )

        component_requested = any(
            keyword in task
            for keyword in (
                "component",
                "component intelligence",
                "supplier",
                "supplier quote",
                "supplier quotes",
                "availability",
                "available",
                "lifecycle",
                "procurement",
                "procurement status",
                "unit price",
                "supplier pricing",
                "quote",
                "quotes",
            )
        )

        bom_requested = any(
            keyword in task
            for keyword in (
                "bom",
                "bill of materials",
                "bom risk",
                "bom cost",
                "bom pricing",
                "overall risk",
                "complete analysis",
                "complete bom",
                "total cost",
                "overall cost",
            )
        )

        risk_requested = any(
            keyword in task
            for keyword in (
                "risk",
                "risky",
                "high risk",
                "critical",
            )
        )

        # Alternative analysis often benefits from BOM/component
        # intelligence first, particularly when the task asks
        # for alternatives based on risk.
        if alternative_requested:
            if risk_requested or bom_requested:
                tools.append(self.BOM_TOOL)

            tools.append(self.ALTERNATIVE_TOOL)

        elif bom_requested or risk_requested:
            tools.append(self.BOM_TOOL)

        elif component_requested:
            tools.append(self.COMPONENT_TOOL)

        else:
            # A generic BOM analysis request defaults to the
            # complete BOM intelligence capability.
            tools.append(self.BOM_TOOL)

        return self._validate_tools(tools)

    def _validate_tools(
        self,
        tools: list[str],
    ) -> list[str]:
        """
        Validate selected tools when strict capability
        validation is enabled.

        Graph orchestration can disable this validation so
        unavailable tools reach the executor, where runtime
        execution failure is recorded consistently.
        """
        if (
            self._registry is None
            or not self._validate_registered_tools
        ):
            return tools

        for tool_name in tools:
            if not self._registry.contains(tool_name):
                raise ValueError(
                    f"Planned tool '{tool_name}' "
                    "is not registered."
                )

        return tools

    def available_capabilities(
        self,
    ) -> tuple[str, ...]:
        """
        Return the names of tools available to the planner.
        """
        if self._registry is None:
            return (
                self.COMPONENT_TOOL,
                self.BOM_TOOL,
                self.ALTERNATIVE_TOOL,
            )

        return self._registry.names()

    def capability_metadata(
        self,
    ) -> tuple[ToolMetadata, ...]:
        """
        Return metadata for all planner-visible tools.
        """
        if self._registry is None:
            return ()

        return self._registry.all_metadata()

    def create_execution_plan(
        self,
        request: AgentRequest,
    ) -> ExecutionPlan:
        """
        Create a structured execution plan for an agent request.

        Tool dependencies are resolved from the registry when
        one is available and the tool exists. Without a registry,
        the existing deterministic dependency behavior is preserved.
        """
        tools = self.plan(request)

        planned_tool_names = set(tools)
        steps: list[PlanStep] = []

        for index, tool_name in enumerate(
            tools,
            start=1,
        ):
            dependencies: list[str] = []

            if (
                self._registry is not None
                and self._registry.contains(tool_name)
            ):
                metadata = self._registry.metadata(
                    tool_name
                )

                for dependency_tool in (
                    metadata.dependencies
                ):
                    if not self._registry.contains(
                        dependency_tool
                    ):
                        raise ValueError(
                            f"Tool '{tool_name}' requires "
                            f"dependency '{dependency_tool}', "
                            "but that dependency is not "
                            "registered."
                        )

                    if (
                        dependency_tool
                        not in planned_tool_names
                    ):
                        raise ValueError(
                            f"Tool '{tool_name}' requires "
                            f"dependency '{dependency_tool}', "
                            "but that dependency is not "
                            "present in the execution plan."
                        )

                    dependency_step = next(
                        (
                            step
                            for step in steps
                            if step.tool_name
                            == dependency_tool
                        ),
                        None,
                    )

                    if dependency_step is None:
                        raise ValueError(
                            f"Tool '{tool_name}' requires "
                            f"dependency '{dependency_tool}', "
                            "but that dependency appears "
                            "after the dependent tool."
                        )

                    dependencies.append(
                        dependency_step.step_id
                    )

            elif (
                self._registry is None
                and tool_name == self.ALTERNATIVE_TOOL
                and steps
            ):
                dependencies.append(
                    steps[-1].step_id
                )

            steps.append(
                PlanStep(
                    step_id=f"step_{index}",
                    tool_name=tool_name,
                    dependencies=dependencies,
                )
            )

        return ExecutionPlan(
            steps=steps,
            metadata={
                "task": request.task.strip(),
                "tool_count": len(steps),
            },
        )