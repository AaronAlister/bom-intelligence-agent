import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.repositories import ComponentRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.availability.models import (
    AvailabilitySummary,
    ProcurementStatus,
)
from backend.app.intelligence.availability.procurement import (
    ComponentProcurementResult,
)
from backend.app.intelligence.component.models import (
    ComponentIntelligenceResult,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
    LifecycleRisk,
    LifecycleStatus,
)
from backend.app.main import app


def make_intelligence(
    *,
    mpn: str,
    manufacturer: str,
    lifecycle_status: LifecycleStatus,
    availability: int,
) -> ComponentIntelligenceResult:

    distributor_result = ComponentEnrichmentResult(
        mpn=mpn,
        manufacturer=manufacturer,
        lifecycle_status=lifecycle_status.value,
        availability=availability,
        source="e2e-test",
    )

    availability_summary = AvailabilitySummary(
        distributors=[],
        total_distributor_quantity=availability,
        distributors_available=(
            1 if availability > 0 else 0
        ),
        distributors_unavailable=0,
        best_available_quantity=availability,
        procurement_status=(
            ProcurementStatus.READY
            if availability > 0
            else ProcurementStatus.UNAVAILABLE
        ),
    )

    procurement = ComponentProcurementResult(
        mpn=mpn,
        manufacturer=manufacturer,
        distributor_results=[
            distributor_result
        ],
        availability=availability_summary,
    )

    lifecycle = LifecycleAssessment(
        status=lifecycle_status,
        eol_date=None,
        last_buy_date=None,
        risk=(
            LifecycleRisk.LOW
            if lifecycle_status
            == LifecycleStatus.ACTIVE
            else LifecycleRisk.HIGH
        ),
        source="e2e-test",
    )

    return ComponentIntelligenceResult(
        mpn=mpn,
        manufacturer=manufacturer,
        procurement=procurement,
        lifecycle=lifecycle,
    )


@pytest.mark.asyncio
async def test_phase5_end_to_end_intelligence_workflow():

    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"E2E-SOURCE-{suffix}"
    alternative_mpn = f"E2E-ALT-{suffix}"

    category = f"E2E-CATEGORY-{suffix}"
    package = f"E2E-PACKAGE-{suffix}"

    async with AsyncSessionLocal() as session:

        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="Texas Instruments",
            category=category,
            package=package,
        )

        alternative = await ComponentRepository.create(
            session,
            mpn=alternative_mpn,
            manufacturer="STMicroelectronics",
            category=category,
            package=package,
        )

        await session.commit()

        source_id = source.id
        alternative_id = alternative.id

    intelligence_service = AsyncMock()

    intelligence_service.analyze.side_effect = (
        lambda *, mpn, manufacturer: (
            make_intelligence(
                mpn=mpn,
                manufacturer=manufacturer or "",
                lifecycle_status=LifecycleStatus.ACTIVE,
                availability=5000,
            )
        )
    )

    source_enrichment = ComponentEnrichmentResult(
        mpn=source_mpn,
        manufacturer="Texas Instruments",
        category=category,
        package=package,
        lifecycle_status="ACTIVE",
        availability=5000,
        source="e2e-test",
    )

    # ---------------------------------------------------------
    # 1. Alternative analysis
    # ---------------------------------------------------------

    from backend.app.services.alternative_component import (
        AlternativeComponentService,
    )

    async with AsyncSessionLocal() as session:

        analysis = (
            await AlternativeComponentService
            .find_alternatives(
                session,
                component_id=source_id,
                source_enrichment=source_enrichment,
                limit=10,
                intelligence_service=intelligence_service,
            )
        )

        assert analysis.source_mpn == source_mpn

        assert len(analysis.candidates) == 1

        candidate = analysis.candidates[0]

        assert (
            candidate.component.mpn
            == alternative_mpn
        )

        assert candidate.category_match is True
        assert candidate.package_match is True
        assert candidate.manufacturer_match is False

        assert candidate.lifecycle_score == 15.0
        assert candidate.availability_score == 10.0

        assert candidate.compatibility_score == 90.0

        assert (
            analysis.best_candidate
            is not None
        )

        assert (
            analysis.best_candidate.component.mpn
            == alternative_mpn
        )

    # ---------------------------------------------------------
    # 2. Persist alternative analysis
    # ---------------------------------------------------------

    from backend.app.services.alternative_workflow import (
        AlternativeWorkflowService,
    )

    async with AsyncSessionLocal() as session:

        analysis, persisted_count = (
            await AlternativeWorkflowService
            .analyze_and_persist(
                session,
                component_id=source_id,
                source_enrichment=source_enrichment,
                limit=10,
                intelligence_service=intelligence_service,
            )
        )

        await session.commit()

        assert analysis.source_mpn == source_mpn

        assert persisted_count == 1

    # ---------------------------------------------------------
    # 3. Verify history API
    # ---------------------------------------------------------

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:

        response = await client.get(
            f"/api/v1/components/"
            f"{source_id}/alternatives/history"
        )

    assert response.status_code == 200

    history = response.json()

    assert (
        history["source_component_id"]
        == source_id
    )

    assert len(history["records"]) == 1

    record = history["records"][0]

    assert (
        record["alternative_component_id"]
        == alternative_id
    )

    assert (
        record["compatibility_score"]
        == 90.0
    )