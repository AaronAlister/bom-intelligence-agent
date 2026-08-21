from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Literal, Protocol

from backend.app.agents.contracts import (
    AgentRequest,
    AgentResponse,
    Evidence,
)
from backend.app.agents.executor import (
    AgentToolExecutor,
)
from backend.app.agents.planner import (
    AgentPlanner,
)
from backend.app.agents.state import (
    AgentState,
    ExecutionPlan,
)


class RAGServiceProtocol(Protocol):
    """
    Interface required by BOMAgent for RAG evidence retrieval.

    BOMAgent depends on the retrieval capability rather than
    the concrete RAGService implementation.
    """

    async def retrieve_evidence(
        self,
        *,
        query: str,
        retrieval_limit: int = 10,
        evidence_limit: int = 5,
    ) -> list[Evidence]:
        ...


class BOMAgent:
    """
    End-to-end deterministic BOM intelligence agent.

    The agent coordinates planning, deterministic tool
    execution, and optional RAG evidence retrieval.
    """

    def __init__(
        self,
        *,
        planner: AgentPlanner,
        executor: AgentToolExecutor,
        rag_service: RAGServiceProtocol | None = None,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._rag_service = rag_service

        self._planner.set_registry(
            self._executor.registry
        )

    async def run(
        self,
        request: AgentRequest,
    ) -> AgentResponse:
        """
        Execute an agent request from planning through
        deterministic tool execution, optional RAG evidence,
        and response synthesis.
        """

        started = perf_counter()

        state = AgentState(
            bom_id=request.bom_id,
            task=request.task,
            context=request.context,
            component_ids=request.component_ids,
            requested_evidence=request.requested_evidence,
            started_at=self._timestamp(),
        )

        try:
            try:
                state.execution_plan = (
                    self._planner.create_execution_plan(
                        request
                    )
                )

                state.planned_tools = [
                    step.tool_name
                    for step in state.execution_plan.steps
                ]

            except ValueError as exc:
                state.status = "failed"
                state.errors.append(str(exc))

                return self._build_response(
                    self._finalize_execution(
                        state,
                        started,
                    )
                )

            state = await self._executor.execute(
                state
            )

            await self._collect_rag_evidence(
                state
            )

            self._collect_outputs(state)

            return self._build_response(
                self._finalize_execution(
                    state,
                    started,
                )
            )

        except Exception as exc:
            state.status = "failed"
            state.errors.append(
                f"Agent execution failed: {exc}"
            )

            return self._build_response(
                self._finalize_execution(
                    state,
                    started,
                )
            )

    async def _collect_rag_evidence(
        self,
        state: AgentState,
    ) -> None:
        """
        Retrieve RAG evidence when requested by the caller.

        RAG failures are isolated from deterministic tool
        execution so that existing intelligence results are
        still returned.
        """

        if not state.requested_evidence:
            return

        if self._rag_service is None:
            state.errors.append(
                "RAG evidence was requested but no "
                "RAG service is configured."
            )

            if state.status == "success":
                state.status = "partial"

            return

        query = self._build_rag_query(
            state
        )

        try:
            evidence = (
                await self._rag_service
                .retrieve_evidence(
                    query=query,
                )
            )

            state.evidence.extend(
                evidence
            )

        except Exception as exc:
            state.errors.append(
                f"RAG evidence retrieval failed: {exc}"
            )

            if state.status == "success":
                state.status = "partial"

    @staticmethod
    def _build_rag_query(
        state: AgentState,
    ) -> str:
        """
        Build a deterministic RAG query from the agent
        task and requested evidence categories.
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

    @staticmethod
    def _collect_outputs(
        state: AgentState,
    ) -> None:
        """
        Extract generic findings, risks, recommendations,
        and evidence from tool results.

        Domain-specific interpretation remains inside the
        intelligence services.
        """

        for result in state.tool_results:
            if result.status != "success":
                continue

            data = result.data

            findings = data.get(
                "findings",
                [],
            )

            if isinstance(
                findings,
                list,
            ):
                state.findings.extend(
                    findings
                )

            risks = data.get(
                "risks",
                [],
            )

            if isinstance(
                risks,
                list,
            ):
                state.risks.extend(
                    risks
                )

            recommendations = data.get(
                "recommendations",
                [],
            )

            if isinstance(
                recommendations,
                list,
            ):
                state.recommendations.extend(
                    recommendations
                )

    @staticmethod
    def _normalize_response_status(
        status: Literal[
            "pending",
            "running",
            "success",
            "partial",
            "failed",
        ],
    ) -> Literal[
        "success",
        "partial",
        "failed",
    ]:
        """
        Convert internal agent lifecycle states into the
        narrower public response status contract.
        """

        if status == "success":
            return "success"

        if status == "partial":
            return "partial"

        if status == "failed":
            return "failed"

        return "failed"

    @staticmethod
    def _calculate_confidence(
        state: AgentState,
    ) -> float:
        """
        Calculate deterministic execution confidence.

        Confidence reflects tool execution completeness,
        not the correctness of the underlying intelligence.
        """

        if not state.executions:
            return 0.0

        successful = sum(
            execution.status == "success"
            for execution in state.executions
        )

        return successful / len(
            state.executions
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(
            UTC
        ).isoformat()

    @staticmethod
    def _finalize_execution(
        state: AgentState,
        started: float,
    ) -> AgentState:
        """
        Finalize top-level agent execution observability.
        """

        state.completed_at = BOMAgent._timestamp()

        state.execution_time_ms = (
            perf_counter() - started
        ) * 1000

        return state

    @staticmethod
    def _build_response(
        state: AgentState,
    ) -> AgentResponse:
        """
        Convert internal AgentState into the public
        AgentResponse contract.
        """

        response_status = (
            BOMAgent._normalize_response_status(
                state.status
            )
        )

        successful_tools = [
            execution.tool_name
            for execution in state.executions
            if execution.status == "success"
        ]

        failed_tools = [
            execution.tool_name
            for execution in state.executions
            if execution.status == "failed"
        ]

        summary = BOMAgent._build_summary(
            state
        )

        confidence = BOMAgent._calculate_confidence(
            state
        )

        execution_metadata: dict[
            str,
            Any,
        ] = {
            "execution_id": getattr(
                state,
                "execution_id",
                "unknown",
            ),
            "started_at": state.started_at,
            "completed_at": state.completed_at,
            "execution_time_ms": state.execution_time_ms,
            "execution_plan": (
                state.execution_plan.model_dump(
                    mode="json"
                )
                if state.execution_plan is not None
                else None
            ),
            "planned_tools": state.planned_tools,
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "tool_count": len(
                state.planned_tools
            ),
            "successful_tool_count": len(
                successful_tools
            ),
            "failed_tool_count": len(
                failed_tools
            ),
            "execution_count": len(
                state.executions
            ),
            "executions": [
                execution.model_dump(
                    mode="json"
                )
                for execution in state.executions
            ],
            "errors": list(state.errors),
            "rag_evidence_requested": bool(
                state.requested_evidence
            ),
            "rag_evidence_count": sum(
                evidence.source == "rag"
                for evidence in state.evidence
            ),
        }

        return AgentResponse(
            agent="bom_intelligence_agent",
            status=response_status,
            bom_id=state.bom_id,
            summary=summary,
            findings=state.findings,
            risks=state.risks,
            recommendations=state.recommendations,
            evidence=state.evidence,
            confidence=confidence,
            execution_metadata=execution_metadata,
        )

    @staticmethod
    def _build_summary(
        state: AgentState,
    ) -> str:
        if state.status == "success":
            return (
                "BOM intelligence analysis completed "
                f"successfully using "
                f"{len(state.executions)} tool(s)."
            )

        if state.status == "partial":
            return (
                "BOM intelligence analysis completed "
                "partially. One or more tools failed "
                "during execution."
            )

        if state.status == "failed":
            if state.errors:
                return (
                    "BOM intelligence analysis failed: "
                    f"{state.errors[0]}"
                )

            return (
                "BOM intelligence analysis failed."
            )

        return (
            "BOM intelligence analysis has not "
            "completed."
        )