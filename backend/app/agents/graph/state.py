from typing import Any, TypedDict

from backend.app.agents.state import (
    AgentState,
)


class GraphState(TypedDict):
    """
    LangGraph orchestration state.

    The existing AgentState remains the authoritative
    domain and execution state. LangGraph owns only the
    orchestration lifecycle around it.
    """

    agent_state: AgentState

    current_node: str

    graph_status: str

    graph_errors: list[str]

    metadata: dict[str, Any]


def create_graph_state(
    agent_state: AgentState,
) -> GraphState:
    """
    Create the initial LangGraph state from an
    existing AgentState.
    """

    return GraphState(
        agent_state=agent_state,
        current_node="start",
        graph_status="pending",
        graph_errors=[],
        metadata={},
    )