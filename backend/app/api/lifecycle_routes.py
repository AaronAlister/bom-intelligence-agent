from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.lifecycle_schemas import (
    LifecycleHistoryResponse,
    LifecycleResponse,
)
from backend.app.db.repositories import (
    ComponentRepository,
    LifecycleRepository,
)
from backend.app.db.session import get_db
from backend.app.intelligence.lifecycle.models import (
    LifecycleRisk,
    LifecycleStatus,
)
from backend.app.models.lifecycle import LifecycleRecord


router = APIRouter(
    prefix="/components",
    tags=["Lifecycle"],
)


def _get_lifecycle_risk(
    status: str,
) -> LifecycleRisk:
    """Map lifecycle status to its corresponding risk."""

    try:
        lifecycle_status = LifecycleStatus(status)
    except ValueError:
        return LifecycleRisk.UNKNOWN

    if lifecycle_status == LifecycleStatus.ACTIVE:
        return LifecycleRisk.LOW

    if lifecycle_status == LifecycleStatus.NRND:
        return LifecycleRisk.MEDIUM

    if lifecycle_status == LifecycleStatus.EOL:
        return LifecycleRisk.HIGH

    if lifecycle_status == LifecycleStatus.OBSOLETE:
        return LifecycleRisk.CRITICAL

    return LifecycleRisk.UNKNOWN


def _to_lifecycle_response(
    record,
) -> LifecycleResponse:
    risk = _get_lifecycle_risk(record.status)

    return LifecycleResponse(
        id=record.id,
        component_id=record.component_id,
        status=record.status,
        risk=risk.value,
        eol_date=record.eol_date,
        last_buy_date=record.last_buy_date,
        created_at=record.created_at,
    )


@router.get(
    "/{component_id}/lifecycle/history",   # <-- CHANGED PATH
    response_model=LifecycleHistoryResponse,
)
async def get_component_lifecycle_history(   # <-- RENAMED FUNCTION
    component_id: int,
    session: AsyncSession = Depends(get_db),
) -> LifecycleHistoryResponse:
    """
    Return lifecycle history for a component.
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

    records = await LifecycleRepository.list_for_component(
        session,
        component_id,
    )

    responses = [
        _to_lifecycle_response(record)
        for record in reversed(records)
    ]

    return LifecycleHistoryResponse(
        component_id=component_id,
        records=responses,
    )