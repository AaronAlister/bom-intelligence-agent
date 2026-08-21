import pytest
from typing import Any

from backend.app.agents.executor import (
    AgentToolExecutor,
)
from backend.app.agents.state import (
    AgentState,
    ToolResult,
)
from backend.app.agents.tools.base import (
    AgentTool,
)
from backend.app.agents.graph.graph import (
    compile_graph,
)
from backend.app.agents.graph.state import (
    create_graph_state,
)
from backend.app.agents.retry import (
    RetryPolicy,
)
from backend.app.agents.contracts import (
    AgentRequest,
    Evidence,
)

def make_state(
    task: str = "Analyze the complete BOM",
) -> AgentState:
    return AgentState(
        bom_id="GRAPH-003",
        task=task,
    )


@pytest.mark.asyncio
async def test_graph_executes_planner_node() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert agent_state.execution_plan is not None
    assert agent_state.planned_tools == [
        "bom_intelligence",
    ]
    assert result["current_node"] == (
        "bom_intelligence"
    )


@pytest.mark.asyncio
async def test_planner_node_creates_execution_plan() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert agent_state.execution_plan is not None

    assert (
        agent_state.execution_plan.steps[0]
        .tool_name
        == "bom_intelligence"
    )


@pytest.mark.asyncio
async def test_planner_node_updates_planned_tools() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert agent_state.planned_tools == [
        "bom_intelligence",
    ]


@pytest.mark.asyncio
async def test_planner_node_preserves_agent_state() -> None:
    graph = compile_graph()

    agent_state = make_state()

    state = create_graph_state(
        agent_state,
    )

    result = await graph.ainvoke(state)

    assert result["agent_state"] is agent_state
    assert (
        result["agent_state"].bom_id
        == "GRAPH-003"
    )


@pytest.mark.asyncio
async def test_planner_node_handles_empty_task() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(task=""),
    )

    result = await graph.ainvoke(state)

    assert result["graph_status"] == "failed"
    assert result["current_node"] == (
        "unsupported"
    )
    assert result["agent_state"].status == "failed"
    assert result["graph_errors"]


@pytest.mark.asyncio
async def test_planner_node_supports_component_request() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(
            task=(
                "Check component availability "
                "and supplier pricing"
            ),
        ),
    )

    result = await graph.ainvoke(state)

    assert result["graph_status"] == "routed"

    assert result["agent_state"].planned_tools == [
        "component_intelligence",
    ]

    assert result["current_node"] == (
        "component_intelligence"
    )


@pytest.mark.asyncio
async def test_graph_routes_bom_request() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    assert result["current_node"] == (
        "bom_intelligence"
    )
    assert result["graph_status"] == "routed"


@pytest.mark.asyncio
async def test_graph_routes_component_request() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(
            task=(
                "Check component availability "
                "and supplier pricing"
            ),
        ),
    )

    result = await graph.ainvoke(state)

    assert result["current_node"] == (
        "component_intelligence"
    )
    assert result["graph_status"] == "routed"


@pytest.mark.asyncio
async def test_graph_routes_alternative_request() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(
            task="Find alternatives",
        ),
    )

    result = await graph.ainvoke(state)

    assert result["current_node"] == (
        "alternative_analysis"
    )
    assert result["graph_status"] == "routed"


@pytest.mark.asyncio
async def test_graph_routes_bom_alternative_request_to_bom_first() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(
            task=(
                "Find alternatives based on "
                "BOM risk"
            ),
        ),
    )

    result = await graph.ainvoke(state)

    assert result["current_node"] == (
        "bom_intelligence"
    )


@pytest.mark.asyncio
async def test_graph_routes_failed_plan_to_unsupported() -> None:
    graph = compile_graph()

    state = create_graph_state(
        make_state(task=""),
    )

    result = await graph.ainvoke(state)

    assert result["current_node"] == (
        "unsupported"
    )
    assert result["graph_status"] == "failed"
    assert result["graph_errors"]


class GraphExecutionTool(AgentTool):
    name = "bom_intelligence"
    description = "Deterministic graph execution test tool."

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
                "executed_by": "graph",
            },
        )


@pytest.mark.asyncio
async def test_graph_executes_real_agent_tool() -> None:
    executor = AgentToolExecutor(
        [GraphExecutionTool()]
    )

    graph = compile_graph(
        executor=executor,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "completed"
    assert result["graph_status"] == "completed"

    assert agent_state.status == "success"

    assert len(agent_state.executions) == 1

    execution = agent_state.executions[0]

    assert execution.tool_name == (
        "bom_intelligence"
    )

    assert execution.status == "success"
    assert execution.attempts == 1

    assert len(agent_state.tool_results) == 1

    tool_result = agent_state.tool_results[0]

    assert tool_result.tool_name == (
        "bom_intelligence"
    )

    assert tool_result.status == "success"


class GraphFailingTool(AgentTool):
    name = "bom_intelligence"
    description = "Deterministic graph failure test tool."

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
            error="Expected graph tool failure.",
        )


@pytest.mark.asyncio
async def test_graph_preserves_tool_failure() -> None:
    executor = AgentToolExecutor(
        [GraphFailingTool()]
    )

    graph = compile_graph(
        executor=executor,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "failed"
    assert result["graph_status"] == "failed"

    assert agent_state.status == "failed"

    assert len(agent_state.executions) == 1

    assert (
        agent_state.executions[0].status
        == "failed"
    )

    assert (
        "Expected graph tool failure."
        in agent_state.errors
    )


@pytest.mark.asyncio
async def test_graph_preserves_missing_tool_failure() -> None:
    executor = AgentToolExecutor([])

    graph = compile_graph(
        executor=executor,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "failed"
    assert result["graph_status"] == "failed"

    assert agent_state.status == "failed"

    assert len(agent_state.executions) == 1

    assert (
        agent_state.executions[0].status
        == "failed"
    )

    assert (
        "Tool 'bom_intelligence' is not registered."
        in agent_state.errors
    )


class PartialAgentToolExecutor(AgentToolExecutor):
    """Deterministic executor returning a partial result."""

    async def execute(
        self,
        state: AgentState,
    ) -> AgentState:
        state.status = "partial"
        return state


@pytest.mark.asyncio
async def test_graph_routes_partial_execution_to_partial() -> None:
    executor = PartialAgentToolExecutor([])

    graph = compile_graph(
        executor=executor,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    assert result["current_node"] == "partial"
    assert result["graph_status"] == "partial"
    assert result["agent_state"].status == "partial"

class GraphRetryableTool(AgentTool):
    """Fails once with a transient timeout, then succeeds."""

    name = "bom_intelligence"
    description = "Transient retry test tool."

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
                "Temporary graph timeout."
            )

        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "attempts": self.attempts,
            },
        )

@pytest.mark.asyncio
async def test_graph_retries_transient_tool_failure() -> None:
    tool = GraphRetryableTool()

    executor = AgentToolExecutor(
        [tool],
        retry_policy=RetryPolicy(
            max_attempts=2,
        ),
    )

    graph = compile_graph(
        executor=executor,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "completed"
    assert result["graph_status"] == "completed"

    assert agent_state.status == "success"

    assert tool.attempts == 2

    assert len(agent_state.executions) == 1

    execution = agent_state.executions[0]

    assert execution.status == "success"
    assert execution.attempts == 2

class GraphAlwaysTimeoutTool(AgentTool):
    """Always raises a retryable timeout."""

    name = "bom_intelligence"
    description = "Persistent timeout test tool."

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

        raise TimeoutError(
            "Persistent graph timeout."
        )

@pytest.mark.asyncio
async def test_graph_fails_after_retry_exhaustion() -> None:
    tool = GraphAlwaysTimeoutTool()

    executor = AgentToolExecutor(
        [tool],
        retry_policy=RetryPolicy(
            max_attempts=2,
        ),
    )

    graph = compile_graph(
        executor=executor,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "failed"
    assert result["graph_status"] == "failed"

    assert agent_state.status == "failed"

    assert tool.attempts == 2

    assert len(agent_state.executions) == 1

    execution = agent_state.executions[0]

    assert execution.status == "failed"
    assert execution.attempts == 2

    assert any(
        "Persistent graph timeout."
        in error
        for error in agent_state.errors
    )

class GraphDeterministicFailureTool(AgentTool):
    """Returns a deterministic failure without raising."""

    name = "bom_intelligence"
    description = "Deterministic failure test tool."

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

        return ToolResult(
            tool_name=self.name,
            status="failed",
            error="Deterministic graph failure.",
        )

@pytest.mark.asyncio
async def test_graph_does_not_retry_deterministic_tool_failure() -> None:
    tool = GraphDeterministicFailureTool()

    executor = AgentToolExecutor(
        [tool],
        retry_policy=RetryPolicy(
            max_attempts=3,
        ),
    )

    graph = compile_graph(
        executor=executor,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "failed"
    assert result["graph_status"] == "failed"

    assert agent_state.status == "failed"

    assert tool.attempts == 1

    assert len(agent_state.executions) == 1

    execution = agent_state.executions[0]

    assert execution.status == "failed"
    assert execution.attempts == 1

    assert (
        "Deterministic graph failure."
        in agent_state.errors
    )

class GraphRetryableConnectionTool(AgentTool):
    """Fails once with ConnectionError, then succeeds."""

    name = "bom_intelligence"
    description = "Transient connection retry test tool."

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
            raise ConnectionError(
                "Temporary connection failure."
            )

        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "attempts": self.attempts,
            },
        )

@pytest.mark.asyncio
async def test_graph_retries_transient_connection_failure() -> None:
    tool = GraphRetryableConnectionTool()

    executor = AgentToolExecutor(
        [tool],
        retry_policy=RetryPolicy(
            max_attempts=2,
        ),
    )

    graph = compile_graph(
        executor=executor,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        ),
    )

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "completed"
    assert result["graph_status"] == "completed"

    assert agent_state.status == "success"

    assert tool.attempts == 2

    execution = agent_state.executions[0]

    assert execution.status == "success"
    assert execution.attempts == 2

class FakeGraphRAGService:
    """Deterministic RAG service for graph integration tests."""

    def __init__(
        self,
        evidence: list[Evidence],
    ) -> None:
        self.evidence = evidence
        self.queries: list[str] = []

    async def retrieve_evidence(
        self,
        *,
        query: str,
        retrieval_limit: int = 10,
        evidence_limit: int = 5,
    ) -> list[Evidence]:
        self.queries.append(query)
        return self.evidence

@pytest.mark.asyncio
async def test_graph_retrieves_rag_evidence() -> None:
    evidence = [
        Evidence(
            source="rag",
            source_id="DOC-001-chunk-0",
            excerpt="Input voltage is 4.5V to 5.5V.",
            metadata={
                "document_id": "DOC-001",
            },
        )
    ]

    rag_service = FakeGraphRAGService(
        evidence=evidence,
    )

    graph = compile_graph(
        executor=AgentToolExecutor(
            [GraphExecutionTool()]
        ),
        rag_service=rag_service,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        )
    )

    state["agent_state"].requested_evidence = [
        "voltage specifications",
    ]

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "completed"
    assert result["graph_status"] == "completed"

    assert len(agent_state.evidence) == 1
    assert agent_state.evidence[0].source == "rag"

    assert rag_service.queries == [
        "Analyze the complete BOM voltage specifications"
    ]

@pytest.mark.asyncio
async def test_graph_marks_partial_when_rag_fails() -> None:
    class FailingGraphRAGService:
        async def retrieve_evidence(
            self,
            *,
            query: str,
            retrieval_limit: int = 10,
            evidence_limit: int = 5,
        ) -> list[Evidence]:
            raise RuntimeError(
                "RAG backend unavailable"
            )

    graph = compile_graph(
        executor=AgentToolExecutor(
            [GraphExecutionTool()]
        ),
        rag_service=FailingGraphRAGService(),
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        )
    )

    state["agent_state"].requested_evidence = [
        "datasheet specifications",
    ]

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "partial"
    assert result["graph_status"] == "partial"

    assert agent_state.status == "partial"
    assert agent_state.evidence == []

    assert agent_state.errors == [
        "RAG evidence retrieval failed: "
        "RAG backend unavailable"
    ]

@pytest.mark.asyncio
async def test_graph_marks_partial_when_rag_is_requested_without_service() -> None:
    graph = compile_graph(
        executor=AgentToolExecutor(
            [GraphExecutionTool()]
        )
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        )
    )

    state["agent_state"].requested_evidence = [
        "datasheet specifications",
    ]

    result = await graph.ainvoke(state)

    agent_state = result["agent_state"]

    assert result["current_node"] == "partial"
    assert result["graph_status"] == "partial"

    assert agent_state.status == "partial"

    assert agent_state.errors == [
        "RAG evidence was requested but no "
        "RAG service is configured."
    ]

@pytest.mark.asyncio
async def test_graph_skips_rag_when_evidence_not_requested() -> None:
    rag_service = FakeGraphRAGService(
        evidence=[]
    )

    graph = compile_graph(
        executor=AgentToolExecutor(
            [GraphExecutionTool()]
        ),
        rag_service=rag_service,
    )

    state = create_graph_state(
        make_state(
            task="Analyze the complete BOM",
        )
    )

    result = await graph.ainvoke(state)

    assert result["current_node"] == "completed"
    assert result["graph_status"] == "completed"

    assert rag_service.queries == []