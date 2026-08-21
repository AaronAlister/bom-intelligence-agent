import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.component_schemas import (
    AlternativeCandidateResponse,
    AlternativeComponentResponse,
    AlternativeHistoryListResponse,
    AlternativeHistoryResponse,
    AlternativePersistResponse,
    AlternativeResponse,
    ComponentEnrichmentResponse,
    ComponentListResponse,
    ComponentResponse,
)
from backend.app.db.repositories import (
    AlternativeRepository,
    ComponentRepository,
)
from backend.app.db.session import get_db
from backend.app.intelligence.enrichment.factory import (
    create_default_orchestrator,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.services.alternative_component import (
    AlternativeComponentService,
)
from backend.app.services.alternative_workflow import (
    AlternativeWorkflowService,
)
from backend.app.services.component_enrichment import (
    ComponentEnrichmentService,
)

router = APIRouter(
    prefix="/components",
    tags=["Components"],
)


# ===== Helper for converting domain candidates to API responses =====
def _to_alternative_candidate_response(
    candidate,
) -> AlternativeCandidateResponse:
    """Convert a ranked alternative into its API response model."""
    component_data = candidate.component

    return AlternativeCandidateResponse(
        component=AlternativeComponentResponse(
            mpn=component_data.mpn or "",
            manufacturer=component_data.manufacturer,
            description=component_data.description,
            category=component_data.category,
            package=component_data.package,
        ),
        compatibility_score=candidate.compatibility_score,
        compatibility_status=candidate.compatibility_status,
        category_match=candidate.category_match,
        package_match=candidate.package_match,
        manufacturer_match=candidate.manufacturer_match,
        lifecycle_score=candidate.lifecycle_score,
        availability_score=candidate.availability_score,
        reasons=list(candidate.reasons),
    )


@router.get(
    "",
    response_model=ComponentListResponse,
)
async def list_components(
    bom_id: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    enrichment_status: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=25,
        ge=1,
        le=100,
    ),
    session: AsyncSession = Depends(get_db),
) -> ComponentListResponse:
    """
    Return a paginated list of components.

    Optional filters:
        bom_id:
            Filter components belonging to a specific BOM (external ID, string).

        search:
            Matches MPN, manufacturer, or description.

        enrichment_status:
            Filters by enrichment status.

        page:
            One-based page number.

        page_size:
            Number of components per page.
    """
    components, total = await ComponentRepository.search(
        session,
        bom_id=bom_id,
        search=search,
        enrichment_status=enrichment_status,
        page=page,
        page_size=page_size,
    )

    total_pages = (
        (total + page_size - 1) // page_size
        if total > 0
        else 0
    )

    return ComponentListResponse(
        components=[
            ComponentResponse.model_validate(component)
            for component in components
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{component_id}",
    response_model=ComponentResponse,
)
async def get_component(
    component_id: int,
    session: AsyncSession = Depends(get_db),
) -> ComponentResponse:
    """
    Return detailed information for a single component.
    """
    component = await ComponentRepository.get_by_id(session, component_id)
    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component {component_id} not found.",
        )
    return ComponentResponse.model_validate(component)


@router.post(
    "/{component_id}/enrich",
    response_model=ComponentEnrichmentResponse,
)
async def enrich_component(
    component_id: int,
    session: AsyncSession = Depends(get_db),
) -> ComponentEnrichmentResponse:
    """
    Enrich a component using the configured provider chain.
    """
    component = await ComponentRepository.get_by_id(session, component_id)
    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component {component_id} not found.",
        )

    orchestrator = create_default_orchestrator()

    try:
        await ComponentEnrichmentService.enrich_with_orchestrator(
            session,
            component,
            orchestrator,
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Component enrichment failed.",
        ) from exc

    return ComponentEnrichmentResponse(
        component=ComponentResponse.model_validate(component),
        status=component.enrichment_status,
    )


@router.get(
    "/{component_id}/alternatives",
    response_model=AlternativeResponse,
)
async def get_component_alternatives(
    component_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> AlternativeResponse:
    """
    Return ranked alternatives for a component.
    """
    component = await ComponentRepository.get_by_id(session, component_id)
    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component {component_id} not found.",
        )

    source_enrichment = ComponentEnrichmentResult(
        mpn=component.mpn,
        manufacturer=component.manufacturer,
        description=component.description,
        category=component.category,
        package=component.package,
        lifecycle_status=None,
        availability=None,
        source="component_catalog",
    )

    try:
        analysis = await AlternativeComponentService.find_alternatives(
            session,
            component_id=component_id,
            source_enrichment=source_enrichment,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Alternative component analysis failed.",
        ) from exc

    # Use the shared helper instead of a local function
    candidates = [
        _to_alternative_candidate_response(candidate)
        for candidate in analysis.candidates
    ]

    best_candidate = candidates[0] if candidates else None

    return AlternativeResponse(
        source_mpn=analysis.source_mpn,
        candidates=candidates,
        best_candidate=best_candidate,
    )


@router.post(
    "/{component_id}/alternatives/analyze",
    response_model=AlternativePersistResponse,
)
async def analyze_and_persist_component_alternatives(
    component_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> AlternativePersistResponse:
    """
    Analyze alternatives for a component and persist the
    resulting recommendation history.
    """
    component = await ComponentRepository.get_by_id(session, component_id)
    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component {component_id} not found.",
        )

    source_enrichment = ComponentEnrichmentResult(
        mpn=component.mpn,
        manufacturer=component.manufacturer,
        description=component.description,
        category=component.category,
        package=component.package,
        lifecycle_status=None,
        availability=None,
        source="component_catalog",
    )

    try:
        analysis, persisted_count = await AlternativeWorkflowService.analyze_and_persist(
            session,
            component_id=component_id,
            source_enrichment=source_enrichment,
            limit=limit,
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Alternative component analysis failed.",
        ) from exc

    # Use the shared helper instead of a local function
    candidates = [
        _to_alternative_candidate_response(candidate)
        for candidate in analysis.candidates
    ]

    best_candidate = candidates[0] if candidates else None

    return AlternativePersistResponse(
        source_mpn=analysis.source_mpn,
        candidates=candidates,
        best_candidate=best_candidate,
        persisted_count=persisted_count,
    )


@router.get(
    "/{component_id}/alternatives/history",
    response_model=AlternativeHistoryListResponse,
)
async def get_alternative_history(
    component_id: int,
    session: AsyncSession = Depends(get_db),
) -> AlternativeHistoryListResponse:
    """
    Return persisted alternative recommendations for a component.
    """
    component = await ComponentRepository.get_by_id(session, component_id)
    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component {component_id} not found.",
        )

    try:
        records = await AlternativeRepository.list_for_source_component(
            session,
            component_id,
        )
        records = list(reversed(records))
        responses = []

        for record in records:
            reasons = json.loads(record.reasons) if record.reasons else []
            responses.append(
                AlternativeHistoryResponse(
                    id=record.id,
                    source_component_id=record.source_component_id,
                    alternative_component_id=record.alternative_component_id,
                    compatibility_score=record.compatibility_score,
                    category_match=record.category_match,
                    package_match=record.package_match,
                    manufacturer_match=record.manufacturer_match,
                    lifecycle_score=record.lifecycle_score,
                    availability_score=record.availability_score,
                    reasons=reasons,
                    created_at=record.created_at,
                )
            )

        return AlternativeHistoryListResponse(
            source_component_id=component_id,
            records=responses,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Alternative history retrieval failed.",
        ) from exc