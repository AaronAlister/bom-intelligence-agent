from time import perf_counter

from backend.app.agents.bom_agent import (
    BOMAgent,
    RAGServiceProtocol,
)
from backend.app.agents.contracts import (
    AgentRequest,
    AgentResponse,
)
from backend.app.agents.executor import (
    AgentToolExecutor,
)
from backend.app.agents.graph.graph import (
    compile_graph,
)
from backend.app.agents.graph.state import (
    create_graph_state,
)
from backend.app.agents.state import (
    AgentState,
)


class GraphBOMAgent:
    """
    BOM agent adapter backed by LangGraph.

    LangGraph owns orchestration while BOMAgent's existing
    response synthesis remains the public response contract.
    """

    def __init__(
        self,
        *,
        executor: AgentToolExecutor,
        rag_service: RAGServiceProtocol | None = None,
    ) -> None:
        self._executor = executor
        self._rag_service = rag_service

        self._graph = compile_graph(
            executor=executor,
            rag_service=rag_service,
        )

    async def run(
        self,
        request: AgentRequest,
    ) -> AgentResponse:
        """
        Execute an AgentRequest through LangGraph and convert
        the resulting AgentState into the public AgentResponse.
        """

        started = perf_counter()

        state = AgentState(
            bom_id=request.bom_id,
            task=request.task,
            context=request.context,
            component_ids=request.component_ids,
            requested_evidence=request.requested_evidence,
            started_at=BOMAgent._timestamp(),
        )

        graph_state = create_graph_state(
            state
        )

        try:
            result = await self._graph.ainvoke(
                graph_state
            )

            final_state = result["agent_state"]

            BOMAgent._collect_outputs(
                final_state
            )

            BOMAgent._finalize_execution(
                final_state,
                started,
            )

            return BOMAgent._build_response(
                final_state
            )

        except Exception as exc:
            final_state = state

            final_state.status = "failed"
            final_state.errors.append(
                f"Agent execution failed: {exc}"
            )

            BOMAgent._finalize_execution(
                final_state,
                started,
            )

            return BOMAgent._build_response(
                final_state
            )