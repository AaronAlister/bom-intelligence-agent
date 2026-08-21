from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.api.intelligence_schemas import (
    BOMIntelligenceResponse,
    ComponentIntelligenceResponse,
    LifecycleResponse,
)
from backend.app.db.repositories import ComponentRepository
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
from backend.app.services.lifecycle_persistence import (   # <-- NEW IMPORT
    LifecyclePersistenceService,
)


component_intelligence_router = APIRouter(
    prefix="/components",
    tags=["Component Intelligence"],
)

bom_intelligence_router = APIRouter(
    prefix="/boms",
    tags=["BOM Intelligence"],
)


def get_intelligence_service() -> ComponentIntelligenceService:
    """
    Construct the default component intelligence service.

    The distributor providers also implement the
    SupplierQuoteProvider interface, so the same provider
    instances are used for enrichment and commercial quotes.
    """

    providers = [
        MouserProvider(),
        ArrowProvider(),
        DigiKeyProvider(),
    ]

    return ComponentIntelligenceService(
        providers=providers,
        quote_providers=providers,
    )


@component_intelligence_router.post(
    "/{component_id}/intelligence",
    response_model=ComponentIntelligenceResponse,
)
async def get_component_intelligence(
    component_id: int,
    quantity: int = Query(
        default=1,
        ge=1,
    ),
    session: AsyncSession = Depends(get_db),
    intelligence_service: ComponentIntelligenceService = Depends(
        get_intelligence_service
    ),
) -> ComponentIntelligenceResponse:
    """
    Return complete intelligence for a persisted component.
    """

    component = await ComponentRepository.get_by_id(
        session,
        component_id,
    )

    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component {component_id} not found.",
        )

    if not component.mpn:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Component {component_id} does not have "
                "a valid MPN."
            ),
        )

    try:
        result = await intelligence_service.analyze(
            mpn=component.mpn,
            manufacturer=component.manufacturer,
            quantity=quantity,
        )

        # Persist the lifecycle assessment
        await LifecyclePersistenceService.persist_component_lifecycle(
            session,
            component_id=component.id,
            assessment=result.lifecycle,
        )

        await session.commit()

    except ValueError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Component intelligence analysis failed.",
        ) from exc

    return ComponentIntelligenceResponse.model_validate(
        result
    )


@component_intelligence_router.get(
    "/{component_id}/lifecycle",
    response_model=LifecycleResponse,
)
async def get_component_lifecycle(
    component_id: int,
    session: AsyncSession = Depends(get_db),
    intelligence_service: ComponentIntelligenceService = Depends(
        get_intelligence_service
    ),
) -> LifecycleResponse:
    """
    Return lifecycle intelligence for a persisted component.
    """

    component = await ComponentRepository.get_by_id(
        session,
        component_id,
    )

    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component {component_id} not found.",
        )

    if not component.mpn:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Component {component_id} does not have "
                "a valid MPN."
            ),
        )

    try:
        result = await intelligence_service.analyze(
            mpn=component.mpn,
            manufacturer=component.manufacturer,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Component lifecycle analysis failed.",
        ) from exc

    return LifecycleResponse.model_validate(
        result.lifecycle
    )


def get_bom_intelligence_service() -> BOMIntelligenceService:
    """
    Construct the BOM intelligence service using the
    default component intelligence service.
    """

    component_service = get_intelligence_service()

    return BOMIntelligenceService(
        component_service=component_service,
    )


@bom_intelligence_router.post(
    "/{bom_id}/intelligence",
    response_model=BOMIntelligenceResponse,
)
async def get_bom_intelligence(
    bom_id: str,
    session: AsyncSession = Depends(get_db),
    intelligence_service: BOMIntelligenceService = Depends(
        get_bom_intelligence_service
    ),
) -> BOMIntelligenceResponse:
    """
    Run complete intelligence analysis for a persisted BOM.
    """

    result = await session.execute(
        select(BOM)
        .options(
            selectinload(BOM.components)
            .selectinload(BOMComponent.component)
        )
        .where(BOM.bom_id == bom_id)
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
            (
                component.id,
                component.mpn,
                component.manufacturer,
                bom_component.quantity,
            )
        )

    try:
        intelligence = await intelligence_service.analyze(
            components=components,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="BOM intelligence analysis failed.",
        ) from exc

    return BOMIntelligenceResponse.model_validate(
        intelligence
    )


router = APIRouter()

router.include_router(
    component_intelligence_router
)

router.include_router(
    bom_intelligence_router
)