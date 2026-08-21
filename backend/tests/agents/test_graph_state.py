from backend.app.agents.graph.state import (
    GraphState,
    create_graph_state,
)
from backend.app.agents.state import (
    AgentState,
)


def make_agent_state() -> AgentState:
    return AgentState(
        bom_id="GRAPH-001",
        task="Analyze the complete BOM",
    )


def test_create_graph_state_initializes_defaults() -> None:
    agent_state = make_agent_state()

    state = create_graph_state(
        agent_state,
    )

    assert state["agent_state"] is agent_state
    assert state["current_node"] == "start"
    assert state["graph_status"] == "pending"
    assert state["graph_errors"] == []
    assert state["metadata"] == {}


def test_graph_state_preserves_agent_state() -> None:
    agent_state = make_agent_state()

    state = create_graph_state(
        agent_state,
    )

    assert (
        state["agent_state"].bom_id
        == "GRAPH-001"
    )

    assert (
        state["agent_state"].task
        == "Analyze the complete BOM"
    )


def test_graph_state_is_typed_as_graph_state() -> None:
    agent_state = make_agent_state()

    state: GraphState = create_graph_state(
        agent_state,
    )

    assert isinstance(
        state["agent_state"],
        AgentState,
    )


def test_graph_state_does_not_duplicate_agent_execution_state() -> None:
    agent_state = make_agent_state()

    state = create_graph_state(
        agent_state,
    )

    assert state["agent_state"].executions == []
    assert state["agent_state"].tool_results == []
    assert state["agent_state"].findings == []
    assert state["agent_state"].risks == []
    assert state["agent_state"].recommendations == []
    assert state["agent_state"].evidence == []