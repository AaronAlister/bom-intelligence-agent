from fastapi import APIRouter, HTTPException

from backend.app.api.agent_routes import (
    router as agent_router,
)
from backend.app.api.bom_routes import (
    router as bom_router,
)
from backend.app.api.component_routes import (
    router as component_router,
)
from backend.app.api.document_routes import (
    router as document_router,
)
from backend.app.api.intelligence_routes import (
    router as intelligence_router,
)
from backend.app.api.lifecycle_routes import (     # <-- ADDED
    router as lifecycle_router,
)
from backend.app.core.config import settings
from backend.app.core.health import check_readiness

router = APIRouter()

router.include_router(
    bom_router
)

router.include_router(
    document_router
)

router.include_router(
    component_router
)

# ===== Lifecycle router registered here =====
router.include_router(
    lifecycle_router
)

router.include_router(
    intelligence_router
)

router.include_router(
    agent_router
)


@router.get("/health", tags=["system"])
async def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/health/live", tags=["system"])
async def liveness():
    return {"status": "alive"}


@router.get("/health/ready", tags=["system"])
async def readiness():
    readiness_result = await check_readiness()

    if readiness_result["status"] != "ready":
        raise HTTPException(
            status_code=503,
            detail=readiness_result,
        )

    return readiness_result