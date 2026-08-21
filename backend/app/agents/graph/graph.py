from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol, cast

from langgraph.graph import END, START, StateGraph

from backend.app.agents.contracts import AgentRequest
from backend.app.agents.executor import AgentToolExecutor
from backend.app.agents.graph.state import GraphState
from backend.app.agents.planner import AgentPlanner
from backend.app.agents.state import AgentState


GraphNode = Callable[
    [GraphState],
    Awaitable[GraphState],
]

RouteName = Literal[
    "bom_intelligence",
    "component_intelligence",
    "alternative_analysis",
    "unsupported",
]

ExecutionRoute = Literal[
    "completed",
    "partial",
    "failed",
]

RAGRoute = Literal[
    "rag",
    "completed",
    "partial",
    "failed",
]


class RAGServiceProtocol(Protocol):
    """
    Interface required by the LangGraph RAG node.

    The graph depends only on the retrieval capability and
    does not depend on the concrete RAG implementation.
    """

    async def retrieve_evidence(
        self,
        *,
        query: str,
        retrieval_limit: int = 10,
        evidence_limit: int = 5,
    ) -> list[Any]:
        ...


async def initialize_node(
    state: GraphState,
) -> GraphState:
    """Initialize the LangGraph execution lifecycle."""
    return {
        **state,
        "current_node": "initialize",
        "graph_status": "running",
    }


def create_planner_node(
    planner: AgentPlanner,
) -> GraphNode:
    """
    Create a planner graph node using the configured planner.
    """

    async def execute_planner(
        state: GraphState,
    ) -> GraphState:
        agent_state = state["agent_state"]

        request = AgentRequest(
            bom_id=agent_state.bom_id,
            task=agent_state.task,
            context=agent_state.context,
            component_ids=agent_state.component_ids,
            requested_evidence=(
                agent_state.requested_evidence
            ),
        )

        try:
            execution_plan = (
                planner.create_execution_plan(
                    request
                )
            )

            agent_state.execution_plan = (
                execution_plan
            )

            agent_state.planned_tools = [
                step.tool_name
                for step in execution_plan.steps
            ]

            return {
                **state,
                "agent_state": agent_state,
                "current_node": "planner",
                "graph_status": "planned",
            }

        except ValueError as exc:
            error = str(exc)

            agent_state.errors.append(error)
            agent_state.status = "failed"

            return {
                **state,
                "agent_state": agent_state,
                "current_node": "planner",
                "graph_status": "failed",
                "graph_errors": [
                    *state["graph_errors"],
                    error,
                ],
            }

    return execute_planner


def route_after_planner(
    state: GraphState,
) -> RouteName:
    """
    Select the graph route from the execution plan.

    The planner decides which tools are required.
    The router only selects the corresponding graph path.
    """

    if state["graph_status"] == "failed":
        return "unsupported"

    execution_plan = (
        state["agent_state"].execution_plan
    )

    if execution_plan is None:
        return "unsupported"

    tool_names = [
        step.tool_name
        for step in execution_plan.steps
    ]

    if not tool_names:
        return "unsupported"

    if "bom_intelligence" in tool_names:
        return "bom_intelligence"

    if "component_intelligence" in tool_names:
        return "component_intelligence"

    if "alternative_analysis" in tool_names:
        return "alternative_analysis"

    return "unsupported"


async def bom_route_node(
    state: GraphState,
) -> GraphState:
    """Select the BOM intelligence execution route."""
    return {
        **state,
        "current_node": "bom_intelligence",
        "graph_status": "routed",
    }


async def component_route_node(
    state: GraphState,
) -> GraphState:
    """Select the component intelligence execution route."""
    return {
        **state,
        "current_node": "component_intelligence",
        "graph_status": "routed",
    }


async def alternative_route_node(
    state: GraphState,
) -> GraphState:
    """Select the alternative analysis execution route."""
    return {
        **state,
        "current_node": "alternative_analysis",
        "graph_status": "routed",
    }


async def unsupported_route_node(
    state: GraphState,
) -> GraphState:
    """Handle a plan that cannot be mapped to a supported route."""
    error = (
        "Execution plan could not be mapped "
        "to a supported graph route."
    )

    agent_state = state["agent_state"]
    agent_state.errors.append(error)
    agent_state.status = "failed"

    return {
        **state,
        "agent_state": agent_state,
        "current_node": "unsupported",
        "graph_status": "failed",
        "graph_errors": [
            *state["graph_errors"],
            error,
        ],
    }


def create_execution_node(
    executor: AgentToolExecutor,
) -> GraphNode:
    """
    Create a LangGraph execution node backed by the
    existing AgentToolExecutor.

    LangGraph owns workflow transitions.
    AgentToolExecutor owns actual tool execution.
    """

    async def execute_node(
        state: GraphState,
    ) -> GraphState:
        agent_state = state["agent_state"]

        if agent_state.execution_plan is None:
            error = (
                "Cannot execute tools without "
                "an execution plan."
            )

            agent_state.status = "failed"
            agent_state.errors.append(error)

            return {
                **state,
                "agent_state": agent_state,
                "current_node": "executor",
                "graph_status": "failed",
                "graph_errors": [
                    *state["graph_errors"],
                    error,
                ],
            }

        try:
            executed_state = (
                await executor.execute(
                    agent_state
                )
            )

            if executed_state.status == "success":
                graph_status = "completed"
            elif executed_state.status == "partial":
                graph_status = "partial"
            else:
                graph_status = "failed"

            return {
                **state,
                "agent_state": executed_state,
                "current_node": "executor",
                "graph_status": graph_status,
            }

        except Exception as exc:
            error = (
                f"Graph execution failed: {exc}"
            )

            agent_state.status = "failed"
            agent_state.errors.append(error)

            return {
                **state,
                "agent_state": agent_state,
                "current_node": "executor",
                "graph_status": "failed",
                "graph_errors": [
                    *state["graph_errors"],
                    error,
                ],
            }

    return execute_node


def route_after_execution(
    state: GraphState,
) -> RAGRoute:
    """
    Decide whether RAG evidence retrieval is required.

    RAG is only attempted when evidence was explicitly
    requested by the caller.

    Existing executor status is preserved when RAG is
    not requested.
    """

    agent_state = state["agent_state"]

    if agent_state.requested_evidence:
        return "rag"

    status = agent_state.status

    if status == "success":
        return "completed"

    if status == "partial":
        return "partial"

    return "failed"


def build_rag_query(
    state: AgentState,
) -> str:
    """
    Build a deterministic RAG query from the agent task
    and requested evidence categories.
    """

    evidence_terms = " ".join(
        term.strip()
        for term in state.requested_evidence
        if term.strip()
    )

    if evidence_terms:
        return (
            f"{state.task.strip()} "
            f"{evidence_terms}"
        ).strip()

    return state.task.strip()


def create_rag_node(
    rag_service: RAGServiceProtocol | None,
) -> GraphNode:
    """
    Create the graph RAG evidence node.

    The concrete RAG implementation remains outside
    the orchestration layer.
    """

    async def rag_node(
        state: GraphState,
    ) -> GraphState:
        agent_state = state["agent_state"]

        if not agent_state.requested_evidence:
            return {
                **state,
                "current_node": "rag",
                "graph_status": state["graph_status"],
            }

        if rag_service is None:
            error = (
                "RAG evidence was requested but no "
                "RAG service is configured."
            )

            agent_state.errors.append(error)

            if agent_state.status == "success":
                agent_state.status = "partial"

            return {
                **state,
                "agent_state": agent_state,
                "current_node": "rag",
                "graph_status": (
                    "partial"
                    if agent_state.status == "partial"
                    else state["graph_status"]
                ),
                "graph_errors": [
                    *state["graph_errors"],
                    error,
                ],
            }

        query = build_rag_query(
            agent_state
        )

        try:
            evidence = (
                await rag_service.retrieve_evidence(
                    query=query,
                )
            )

            agent_state.evidence.extend(
                evidence
            )

            if agent_state.status == "success":
                graph_status = "rag_completed"
            elif agent_state.status == "partial":
                graph_status = "partial"
            else:
                graph_status = "failed"

            return {
                **state,
                "agent_state": agent_state,
                "current_node": "rag",
                "graph_status": graph_status,
            }

        except Exception as exc:
            error = (
                "RAG evidence retrieval failed: "
                f"{exc}"
            )

            agent_state.errors.append(error)

            if agent_state.status == "success":
                agent_state.status = "partial"

            graph_status = (
                "partial"
                if agent_state.status == "partial"
                else "failed"
            )

            return {
                **state,
                "agent_state": agent_state,
                "current_node": "rag",
                "graph_status": graph_status,
                "graph_errors": [
                    *state["graph_errors"],
                    error,
                ],
            }

    return rag_node


def route_after_rag(
    state: GraphState,
) -> ExecutionRoute:
    """
    Route according to the final AgentState status after RAG.
    """

    status = state["agent_state"].status

    if status == "success":
        return "completed"

    if status == "partial":
        return "partial"

    return "failed"


async def completed_node(
    state: GraphState,
) -> GraphState:
    """Mark successful graph completion."""
    return {
        **state,
        "current_node": "completed",
        "graph_status": "completed",
    }


async def partial_node(
    state: GraphState,
) -> GraphState:
    """Mark partial graph completion."""
    return {
        **state,
        "current_node": "partial",
        "graph_status": "partial",
    }


async def failed_node(
    state: GraphState,
) -> GraphState:
    """Mark failed graph completion."""
    return {
        **state,
        "current_node": "failed",
        "graph_status": "failed",
    }


def build_graph(
    executor: AgentToolExecutor | None = None,
    rag_service: RAGServiceProtocol | None = None,
    planner: AgentPlanner | None = None,
) -> StateGraph:
    """
    Build the LangGraph orchestration graph.
    """

    # Configure planner: disable strict tool validation when no explicit
    # planner is given so that missing tools reach the executor.
    configured_planner = (
        planner
        or AgentPlanner(
            validate_registered_tools=False,
        )
    )

    # Provide registry for dependency metadata only if we are using the
    # default planner (no explicit planner passed) and an executor exists.
    if (
        executor is not None
        and planner is None
    ):
        configured_planner.set_registry(
            executor.registry
        )

    builder = StateGraph(GraphState)

    builder.add_node(
        "initialize",
        initialize_node,
    )

    builder.add_node(
        "planner",
        cast(
            Any,
            create_planner_node(
                configured_planner
            ),
        ),
    )

    builder.add_node(
        "bom_intelligence",
        bom_route_node,
    )

    builder.add_node(
        "component_intelligence",
        component_route_node,
    )

    builder.add_node(
        "alternative_analysis",
        alternative_route_node,
    )

    builder.add_node(
        "unsupported",
        unsupported_route_node,
    )

    builder.add_node(
        "completed",
        completed_node,
    )

    builder.add_node(
        "partial",
        partial_node,
    )

    builder.add_node(
        "failed",
        failed_node,
    )

    if executor is not None:
        execution_node = create_execution_node(
            executor
        )

        builder.add_node(
            "executor",
            cast(Any, execution_node),
        )

        rag_node = create_rag_node(
            rag_service
        )

        builder.add_node(
            "rag",
            cast(Any, rag_node),
        )

    builder.add_edge(
        START,
        "initialize",
    )

    builder.add_edge(
        "initialize",
        "planner",
    )

    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "bom_intelligence": (
                "bom_intelligence"
            ),
            "component_intelligence": (
                "component_intelligence"
            ),
            "alternative_analysis": (
                "alternative_analysis"
            ),
            "unsupported": "unsupported",
        },
    )

    if executor is not None:
        builder.add_edge(
            "bom_intelligence",
            "executor",
        )

        builder.add_edge(
            "component_intelligence",
            "executor",
        )

        builder.add_edge(
            "alternative_analysis",
            "executor",
        )

        builder.add_conditional_edges(
            "executor",
            route_after_execution,
            {
                "rag": "rag",
                "completed": "completed",
                "partial": "partial",
                "failed": "failed",
            },
        )

        builder.add_conditional_edges(
            "rag",
            route_after_rag,
            {
                "completed": "completed",
                "partial": "partial",
                "failed": "failed",
            },
        )

    else:
        builder.add_edge(
            "bom_intelligence",
            END,
        )

        builder.add_edge(
            "component_intelligence",
            END,
        )

        builder.add_edge(
            "alternative_analysis",
            END,
        )

    builder.add_edge(
        "completed",
        END,
    )

    builder.add_edge(
        "partial",
        END,
    )

    builder.add_edge(
        "failed",
        END,
    )

    builder.add_edge(
        "unsupported",
        END,
    )

    return builder


def compile_graph(
    executor: AgentToolExecutor | None = None,
    rag_service: RAGServiceProtocol | None = None,
    planner: AgentPlanner | None = None,
):
    """Compile the Phase 12.8 graph."""
    return build_graph(
        executor=executor,
        rag_service=rag_service,
        planner=planner,
    ).compile()