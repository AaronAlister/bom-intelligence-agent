from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.agents.contracts import (
    AgentRequest,
    AgentResponse,
)
from backend.app.agents.executor import AgentToolExecutor
from backend.app.agents.graph.agent import GraphBOMAgent
from backend.app.agents.tools.alternative import (
    AlternativeTool,
)
from backend.app.agents.tools.bom import (
    BOMIntelligenceTool,
)
from backend.app.agents.tools.component import (
    ComponentIntelligenceTool,
)
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.intelligence.bom.service import (
    BOMIntelligenceService,
)
from backend.app.intelligence.component.service import (
    ComponentIntelligenceService,
)
from backend.app.intelligence.enrichment.arrow import (
    ArrowProvider,
)
from backend.app.intelligence.enrichment.digikey import (
    DigiKeyProvider,
)
from backend.app.intelligence.enrichment.mouser import (
    MouserProvider,
)
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.rag.embedding_factory import (
    build_embedding_provider,
)
from backend.app.rag.evidence import (
    RAGEvidenceBuilder,
)
from backend.app.rag.reranker import (
    RAGReranker,
)
from backend.app.rag.retriever import (
    RAGRetriever,
)
from backend.app.rag.service import (
    RAGService,
)
from backend.app.rag.vector_store import (
    QdrantVectorStore,
)


router = APIRouter(
    prefix="/boms",
    tags=["BOM Agent"],
)


def get_agent(
    session: AsyncSession = Depends(get_db),
) -> GraphBOMAgent:
    """
    Construct the BOM Intelligence Agent using the existing
    deterministic intelligence services and the RAG pipeline.
    """

    providers = [
        MouserProvider(),
        ArrowProvider(),
        DigiKeyProvider(),
    ]

    component_service = ComponentIntelligenceService(
        providers=providers,
        quote_providers=providers,
    )

    bom_service = BOMIntelligenceService(
        component_service=component_service,
    )

    tools = [
        ComponentIntelligenceTool(
            component_service,
        ),
        BOMIntelligenceTool(
            bom_service,
        ),
        AlternativeTool(
            session,
            intelligence_service=component_service,
        ),
    ]

    embedding_provider = build_embedding_provider(
        provider=settings.embedding_provider,
        dimension=settings.embedding_dimension,
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )

    qdrant_client = QdrantClient(
        url=settings.qdrant_url,
    )

    vector_store = QdrantVectorStore(
        qdrant_client,
        collection_name=settings.qdrant_collection,
        vector_size=embedding_provider.dimension,
    )

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    reranker = RAGReranker()

    evidence_builder = RAGEvidenceBuilder()

    rag_service = RAGService(
        retriever=retriever,
        reranker=reranker,
        evidence_builder=evidence_builder,
    )

    executor = AgentToolExecutor(tools)

    return GraphBOMAgent(
        executor=executor,
        rag_service=rag_service,
    )


@router.post(
    "/{bom_id}/agent",
    response_model=AgentResponse,
)
async def run_bom_agent(
    bom_id: int,
    request: AgentRequest,
    session: AsyncSession = Depends(get_db),
    agent: GraphBOMAgent = Depends(get_agent),
) -> AgentResponse:
    """
    Run the BOM Intelligence Agent for a persisted BOM.
    """

    result = await session.execute(
        select(BOM)
        .options(
            selectinload(BOM.components)
            .selectinload(BOMComponent.component)
        )
        .where(BOM.id == bom_id)
    )

    bom = result.scalar_one_or_none()

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail=f"BOM {bom_id} not found.",
        )

    if not bom.components:
        raise HTTPException(
            status_code=422,
            detail=(
                f"BOM {bom_id} contains no components."
            ),
        )

    components = []

    for bom_component in bom.components:
        component = bom_component.component

        if not component.mpn:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Component {component.id} in BOM "
                    f"{bom_id} does not have a valid MPN."
                ),
            )

        components.append(
            {
                "component_id": component.id,
                "mpn": component.mpn,
                "manufacturer": component.manufacturer,
                "quantity": bom_component.quantity,
                "description": component.description,
                "category": component.category,
                "package": component.package,
            }
        )

    component_ids = [
        str(component["component_id"])
        for component in components
    ]

    agent_request = request.model_copy(
        update={
            "bom_id": str(bom_id),
            "component_ids": component_ids,
            "context": {
                **request.context,
                "components": components,
                "alternative_components": components,
            },
        }
    )

    try:
        return await agent.run(agent_request)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="BOM agent execution failed.",
        ) from exc