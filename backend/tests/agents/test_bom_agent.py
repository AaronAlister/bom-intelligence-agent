from typing import Any

import pytest

from backend.app.agents.bom_agent import (
    BOMAgent,
)
from backend.app.agents.contracts import (
    AgentRequest,
    Evidence,
)
from backend.app.agents.executor import (
    AgentToolExecutor,
)
from backend.app.agents.planner import (
    AgentPlanner,
)
from backend.app.agents.retry import RetryPolicy
from backend.app.agents.state import (
    AgentState,
    ExecutionPlan,
    PlanStep,
    ToolResult,
)
from backend.app.agents.tools.base import (
    AgentTool,
)
from backend.app.rag.models import (
    DocumentChunk,
    RetrievedChunk,
)


class SuccessfulBOMTool(AgentTool):
    name = "bom_intelligence"
    description = "Test BOM intelligence."

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
                "findings": [
                    {
                        "type": "cost",
                        "value": 125.50,
                    }
                ],
                "risks": [
                    {
                        "component_id": "1",
                        "severity": "HIGH",
                    }
                ],
                "recommendations": [
                    {
                        "action": "review",
                        "component_id": "1",
                    }
                ],
            },
            evidence=[
                Evidence(
                    source="test",
                    source_id="bom-001",
                    excerpt="Test evidence",
                )
            ],
        )


class FailingBOMTool(AgentTool):
    name = "bom_intelligence"
    description = "Test failing BOM intelligence."

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
            error="BOM intelligence unavailable.",
        )


class AlternativeTool(AgentTool):
    name = "alternative_analysis"
    description = "Test alternatives."

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
                "findings": [
                    {
                        "type": "alternative",
                        "component_id": "1",
                    }
                ]
            },
        )


class RetryingBOMTool(AgentTool):
    """
    BOM tool that fails on first attempt but succeeds on retry.
    """

    name = "bom_intelligence"
    description = "BOM intelligence with transient failure."

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
            raise TimeoutError("Temporary timeout during BOM analysis.")
        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "findings": [
                    {
                        "type": "cost",
                        "value": 250.75,
                    }
                ],
                "risks": [
                    {
                        "component_id": "1",
                        "severity": "HIGH",
                    }
                ],
                "recommendations": [
                    {
                        "action": "review",
                        "component_id": "1",
                        "message": "BOM analysis recovered.",
                    }
                ],
            },
            evidence=[
                Evidence(
                    source="bom_intelligence",
                    source_id="bom-retry",
                    excerpt="Recovered BOM evidence.",
                )
            ],
        )


class DependentAlternativeTool(AgentTool):
    """
    Alternative tool that requires BOM intelligence output.

    Used to verify dependency propagation through the
    complete BOMAgent workflow.
    """

    name = "alternative_analysis"
    description = "Alternative analysis requiring BOM output."

    dependencies: tuple[str, ...] = (
        "bom_intelligence",
    )

    def __init__(self) -> None:
        self.received_context: dict[str, Any] | None = None

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        self.received_context = context

        step_outputs = context.get(
            "step_outputs",
            {},
        )

        if not isinstance(
            step_outputs,
            dict,
        ):
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error=(
                    "Missing step output context."
                ),
            )

        bom_output = step_outputs.get(
            "step_1"
        )

        if not isinstance(
            bom_output,
            dict,
        ):
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error=(
                    "BOM step output was not "
                    "propagated."
                ),
            )

        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "findings": [
                    {
                        "type": "alternative",
                        "component_id": "1",
                        "based_on_bom": True,
                    }
                ],
            },
        )


class FakeRAGService:
    """Deterministic RAG service for agent integration tests."""

    def __init__(
        self,
        *,
        evidence: list[Evidence] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.evidence = evidence or []
        self.error = error
        self.calls: list[
            tuple[str, int, int]
        ] = []

    async def retrieve_evidence(
        self,
        *,
        query: str,
        retrieval_limit: int = 10,
        evidence_limit: int = 5,
    ) -> list[Evidence]:
        self.calls.append(
            (
                query,
                retrieval_limit,
                evidence_limit,
            )
        )

        if self.error is not None:
            raise self.error

        return self.evidence


def build_agent(
    tools: list[AgentTool],
) -> BOMAgent:
    return BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(tools),
    )


@pytest.mark.asyncio
async def test_agent_runs_complete_bom_analysis():
    agent = build_agent(
        [SuccessfulBOMTool()]
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task="Analyze the complete BOM",
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "success"
    assert response.agent == (
        "bom_intelligence_agent"
    )
    assert response.bom_id == "BOM-001"

    assert len(response.findings) == 1
    assert len(response.risks) == 1
    assert len(response.recommendations) == 1
    assert len(response.evidence) == 1
    assert response.evidence[0].source == "test"
    assert (
        response.evidence[0].source_id
        == "bom-001"
    )
    assert (
        response.evidence[0].excerpt
        == "Test evidence"
    )

    assert response.execution_metadata[
        "planned_tools"
    ] == ["bom_intelligence"]

    assert response.execution_metadata[
        "successful_tools"
    ] == ["bom_intelligence"]


@pytest.mark.asyncio
async def test_agent_supports_multiple_tools():
    agent = build_agent(
        [
            SuccessfulBOMTool(),
            AlternativeTool(),
        ]
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task=(
            "Find alternatives for high-risk "
            "components"
        ),
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "success"

    assert response.execution_metadata[
        "planned_tools"
    ] == [
        "bom_intelligence",
        "alternative_analysis",
    ]

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 2

    assert len(response.findings) == 2


@pytest.mark.asyncio
async def test_agent_recovers_from_transient_failure_and_runs_dependent_tool():
    bom_tool = RetryingBOMTool()
    alternative_tool = DependentAlternativeTool()

    agent = BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(
            [bom_tool, alternative_tool],
            retry_policy=RetryPolicy(max_attempts=2),
        ),
    )

    request = AgentRequest(
        bom_id="BOM-E2E-RETRY",
        task=(
            "Find alternatives for high-risk "
            "components"
        ),
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "success"

    assert response.execution_metadata[
        "planned_tools"
    ] == [
        "bom_intelligence",
        "alternative_analysis",
    ]

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 2

    assert response.execution_metadata[
        "failed_tool_count"
    ] == 0

    assert response.execution_metadata[
        "execution_count"
    ] == 2

    assert bom_tool.attempts == 2

    assert alternative_tool.received_context is not None

    step_outputs = (
        alternative_tool.received_context.get(
            "step_outputs",
            {},
        )
    )

    assert isinstance(
        step_outputs,
        dict,
    )

    assert step_outputs["step_1"]["recommendations"][0][
        "message"
    ] == "BOM analysis recovered."

    assert len(response.findings) == 2


@pytest.mark.asyncio
async def test_agent_rejects_plan_with_unavailable_tool():
    agent = build_agent(
        [SuccessfulBOMTool()]
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task=(
            "Find alternatives for high-risk "
            "components"
        ),
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "failed"

    assert (
        "not registered"
        in response.summary
    )


@pytest.mark.asyncio
async def test_agent_returns_failed_when_all_tools_fail():
    agent = build_agent(
        [FailingBOMTool()]
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task="Analyze the complete BOM",
    )

    response = await agent.run(request)

    assert response.status == "failed"

    assert response.bom_id == "BOM-001"

    assert response.execution_metadata[
        "failed_tool_count"
    ] == 1

    assert (
        "BOM intelligence unavailable."
        in response.summary
    )


@pytest.mark.asyncio
async def test_agent_rejects_empty_task():
    agent = build_agent(
        [SuccessfulBOMTool()]
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task="",
    )

    response = await agent.run(request)

    assert response.status == "failed"

    assert (
        "Agent task cannot be empty"
        in response.summary
    )


@pytest.mark.asyncio
async def test_agent_preserves_tool_execution_metadata():
    agent = build_agent(
        [SuccessfulBOMTool()]
    )

    request = AgentRequest(
        bom_id="BOM-002",
        task="Analyze BOM risk",
    )

    response = await agent.run(request)

    metadata = response.execution_metadata

    assert metadata["tool_count"] == 1
    assert metadata["execution_count"] == 1
    assert metadata["successful_tool_count"] == 1
    assert metadata["failed_tool_count"] == 0


@pytest.mark.asyncio
async def test_agent_confidence_is_one_when_all_tools_succeed():
    agent = build_agent(
        [SuccessfulBOMTool()]
    )
    request = AgentRequest(
        bom_id="BOM-001",
        task="Analyze the complete BOM",
    )
    response = await agent.run(request)
    assert response.status == "success"
    assert response.confidence == 1.0


@pytest.mark.asyncio
async def test_agent_confidence_is_zero_when_plan_is_invalid():
    agent = build_agent(
        [SuccessfulBOMTool()]
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task=(
            "Find alternatives for high-risk "
            "components"
        ),
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "failed"
    assert response.confidence == 0.0


@pytest.mark.asyncio
async def test_agent_confidence_is_zero_when_tool_fails():
    agent = build_agent(
        [FailingBOMTool()]
    )
    request = AgentRequest(
        bom_id="BOM-001",
        task="Analyze the complete BOM",
    )
    response = await agent.run(request)
    assert response.status == "failed"
    assert response.confidence == 0.0


@pytest.mark.asyncio
async def test_agent_collects_rag_evidence():
    retrieved_chunk = RetrievedChunk(
        chunk=DocumentChunk(
            chunk_id="chunk-001",
            document_id="doc-001",
            text="Supplier risk evidence",
            chunk_index=0,
        ),
        score=0.91,
    )

    rag_evidence = Evidence(
        source="rag",
        source_id=retrieved_chunk.chunk.chunk_id,
        excerpt=retrieved_chunk.chunk.text,
    )

    rag_service = FakeRAGService(
        evidence=[rag_evidence]
    )

    agent = BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(
            [SuccessfulBOMTool()]
        ),
        rag_service=rag_service,
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task="Analyze BOM risk",
        requested_evidence=[
            "supplier",
        ],
    )

    response = await agent.run(request)

    assert response.status == "success"

    assert rag_service.calls == [
        (
            "Analyze BOM risk supplier",
            10,
            5,
        )
    ]

    assert rag_evidence in response.evidence

    assert (
        response.execution_metadata[
            "rag_evidence_requested"
        ]
        is True
    )

    assert (
        response.execution_metadata[
            "rag_evidence_count"
        ]
        == 1
    )


@pytest.mark.asyncio
async def test_agent_marks_partial_when_rag_requested_without_service():
    agent = BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(
            [SuccessfulBOMTool()]
        ),
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task="Analyze BOM risk",
        requested_evidence=[
            "supplier",
        ],
    )

    response = await agent.run(request)

    assert response.status == "partial"

    assert len(response.findings) == 1
    assert len(response.risks) == 1

    assert (
        "no RAG service is configured"
        in response.execution_metadata[
            "errors"
        ][0]
    )

    assert (
        response.execution_metadata[
            "rag_evidence_requested"
        ]
        is True
    )

    assert (
        response.execution_metadata[
            "rag_evidence_count"
        ]
        == 0
    )


@pytest.mark.asyncio
async def test_agent_handles_empty_requested_evidence():
    rag_service = FakeRAGService()

    agent = BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(
            [SuccessfulBOMTool()]
        ),
        rag_service=rag_service,
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task="Analyze BOM risk",
        requested_evidence=[],
    )

    response = await agent.run(request)

    assert response.status == "success"

    assert rag_service.calls == []

    assert (
        response.execution_metadata[
            "rag_evidence_requested"
        ]
        is False
    )


@pytest.mark.asyncio
async def test_agent_uses_task_when_requested_evidence_terms_are_blank():
    rag_service = FakeRAGService()

    agent = BOMAgent(
        planner=AgentPlanner(),
        executor=AgentToolExecutor(
            [SuccessfulBOMTool()]
        ),
        rag_service=rag_service,
    )

    request = AgentRequest(
        bom_id="BOM-001",
        task="Analyze BOM risk",
        requested_evidence=[
            " ",
            "",
        ],
    )

    response = await agent.run(request)

    assert response.status == "success"

    assert len(rag_service.calls) == 1

    query, _, _ = rag_service.calls[0]

    assert query == "Analyze BOM risk"

@pytest.mark.asyncio
async def test_agent_skips_dependent_tool_after_failure():
    class FailingBOMTool(AgentTool):
        name = "bom_intelligence"
        description = "Always fails."

        async def execute(
            self,
            *,
            bom_id: str,
            component_ids: list[str],
            context: dict[str, Any],
        ) -> ToolResult:
            raise RuntimeError(
                "Permanent BOM failure."
            )

    alternative_tool = DependentAlternativeTool()

    agent = build_agent(
        [
            FailingBOMTool(),
            alternative_tool,
        ]
    )

    request = AgentRequest(
        bom_id="BOM-E2E-PARTIAL",
        task=(
            "Find alternatives for high-risk "
            "components"
        ),
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "partial"

    assert response.execution_metadata[
        "planned_tools"
    ] == [
        "bom_intelligence",
        "alternative_analysis",
    ]

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 0

    assert response.execution_metadata[
        "failed_tool_count"
    ] == 1

    assert response.execution_metadata[
        "execution_count"
    ] == 2

    assert (
        response.execution_metadata[
            "executions"
        ][0]["status"]
        == "failed"
    )

    assert (
        response.execution_metadata[
            "executions"
        ][1]["status"]
        == "skipped"
    )

    assert alternative_tool.received_context is None

    assert response.confidence == 0.0

@pytest.mark.asyncio
async def test_agent_skips_dependent_tool_after_retry_exhaustion():
    class AlwaysTimeoutBOMTool(AgentTool):
        name = "bom_intelligence"
        description = "Always times out."

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
                "Persistent BOM timeout."
            )

    bom_tool = AlwaysTimeoutBOMTool()
    alternative_tool = DependentAlternativeTool()

    agent = build_agent(
        [
            bom_tool,
            alternative_tool,
        ]
    )

    request = AgentRequest(
        bom_id="BOM-E2E-RETRY-EXHAUSTED",
        task=(
            "Find alternatives for high-risk "
            "components"
        ),
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "partial"

    assert bom_tool.attempts == 2

    assert response.execution_metadata[
        "planned_tools"
    ] == [
        "bom_intelligence",
        "alternative_analysis",
    ]

    assert response.execution_metadata[
        "execution_count"
    ] == 2

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 0

    assert response.execution_metadata[
        "failed_tool_count"
    ] == 1

    executions = response.execution_metadata[
        "executions"
    ]

    assert executions[0]["status"] == "failed"
    assert executions[0]["attempts"] == 2

    assert executions[1]["status"] == "skipped"

    assert alternative_tool.received_context is None

    assert any(
        "Persistent BOM timeout."
        in error
        for error in response.execution_metadata[
            "errors"
        ]
    )

@pytest.mark.asyncio
async def test_agent_rejects_invalid_execution_plan_before_tool_execution():
    execution_log: list[str] = []

    class RecordingBOMTool(AgentTool):
        name = "bom_intelligence"
        description = "Records whether execution occurred."

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
                status="success",
                data={
                    "findings": [
                        {
                            "type": "unexpected",
                        }
                    ]
                },
            )

    class CyclicPlanner(AgentPlanner):
        def create_execution_plan(
            self,
            request: AgentRequest,
        ) -> ExecutionPlan:
            return ExecutionPlan(
                steps=[
                    PlanStep(
                        step_id="step_1",
                        tool_name="bom_intelligence",
                        dependencies=["step_2"],
                    ),
                    PlanStep(
                        step_id="step_2",
                        tool_name="bom_intelligence",
                        dependencies=["step_1"],
                    ),
                ]
            )

    executor = AgentToolExecutor(
        [RecordingBOMTool()]
    )

    agent = BOMAgent(
        planner=CyclicPlanner(),
        executor=executor,
    )

    request = AgentRequest(
        bom_id="BOM-E2E-INVALID",
        task="Analyze the complete BOM",
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "failed"

    assert execution_log == []

    assert response.execution_metadata[
        "execution_count"
    ] == 0

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 0

    assert response.execution_metadata[
        "failed_tool_count"
    ] == 0

    assert any(
        "dependency cycle" in error
        for error in response.execution_metadata[
            "errors"
        ]
    )

@pytest.mark.asyncio
async def test_agent_rejects_mismatched_tool_result() -> None:
    class MismatchedResultTool(AgentTool):
        name = "bom_intelligence"
        description = "Returns a result for another tool."

        async def execute(
            self,
            *,
            bom_id: str,
            component_ids: list[str],
            context: dict[str, Any],
        ) -> ToolResult:
            return ToolResult(
                tool_name="component_intelligence",
                status="success",
                data={
                    "findings": [
                        {
                            "type": "corrupted_result",
                        }
                    ]
                },
            )

    agent = build_agent(
        [MismatchedResultTool()]
    )

    request = AgentRequest(
        bom_id="BOM-E2E-CORRUPTED",
        task="Analyze the complete BOM",
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "failed"

    assert response.execution_metadata[
        "execution_count"
    ] == 1

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 0

    assert response.execution_metadata[
        "failed_tool_count"
    ] == 1

    assert response.execution_metadata[
        "successful_tools"
    ] == []

    assert response.execution_metadata[
        "failed_tools"
    ] == [
        "bom_intelligence"
    ]

    assert response.findings == []

    assert any(
        "returned a result for "
        "'component_intelligence'"
        in error
        for error in response.execution_metadata[
            "errors"
        ]
    )

@pytest.mark.asyncio
async def test_agent_rejects_invalid_tool_result_type() -> None:
    class InvalidResultTypeTool(AgentTool):
        name = "bom_intelligence"
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
                "data": {
                    "findings": [
                        {
                            "type": "invalid",
                        }
                    ]
                },
            }

            return invalid_result  # type: ignore[return-value]

    agent = build_agent(
        [InvalidResultTypeTool()]
    )

    request = AgentRequest(
        bom_id="BOM-E2E-INVALID-TYPE",
        task="Analyze the complete BOM",
        component_ids=["1"],
    )

    response = await agent.run(request)

    assert response.status == "failed"

    assert response.execution_metadata[
        "execution_count"
    ] == 1

    assert response.execution_metadata[
        "successful_tool_count"
    ] == 0

    assert response.execution_metadata[
        "failed_tool_count"
    ] == 1

    assert response.findings == []

    assert any(
        "invalid result type"
        in error
        for error in response.execution_metadata[
            "errors"
        ]
    )