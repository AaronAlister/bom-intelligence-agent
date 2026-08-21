import uuid
from unittest.mock import AsyncMock

import pytest

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
from backend.app.services.alternative_component import (
    AlternativeComponentService,
)


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
        source="test",
    )

    availability_summary = AvailabilitySummary(
        distributors=[],
        total_distributor_quantity=availability,
        distributors_available=1 if availability > 0 else 0,
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
        source="test",
    )

    return ComponentIntelligenceResult(
        mpn=mpn,
        manufacturer=manufacturer,
        procurement=procurement,
        lifecycle=lifecycle,
    )


@pytest.mark.asyncio
async def test_lifecycle_and_availability_affect_alternative_score():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"INTEL-SOURCE-{suffix}"
    alternative_mpn = f"INTEL-ALT-{suffix}"
    alternative_manufacturer = f"STMicroelectronics-{suffix}"  # <-- NEW

    category = f"INTEL-CATEGORY-{suffix}"
    package = f"INTEL-PACKAGE-{suffix}"

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
            manufacturer=alternative_manufacturer,  # <-- MODIFIED
            category=category,
            package=package,
        )

        await session.commit()

        source_id = source.id

    intelligence_service = AsyncMock()

    intelligence_service.analyze.return_value = (
        make_intelligence(
            mpn=alternative_mpn,
            manufacturer=alternative_manufacturer,  # <-- MODIFIED
            lifecycle_status=LifecycleStatus.ACTIVE,
            availability=5000,
        )
    )

    source_enrichment = ComponentEnrichmentResult(
        mpn=source_mpn,
        manufacturer="Texas Instruments",
        category=category,
        package=package,
        lifecycle_status="ACTIVE",
        availability=5000,
        source="test",
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

        print(
            "ANALYZE CALLS:",
            intelligence_service.analyze.await_args_list,
        )

        assert len(analysis.candidates) == 1

        candidate = analysis.candidates[0]

        assert candidate.component.mpn == alternative_mpn

        assert candidate.lifecycle_score == 15.0
        assert candidate.availability_score == 10.0

        assert candidate.compatibility_score == 90.0

        intelligence_service.analyze.assert_awaited_once_with(
            mpn=alternative_mpn,
            manufacturer=alternative_manufacturer,  # <-- MODIFIED
        )


@pytest.mark.asyncio
async def test_poor_lifecycle_and_availability_reduce_score():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"INTEL-SOURCE-{suffix}"
    alternative_mpn = f"INTEL-ALT-{suffix}"

    category = f"INTEL-CATEGORY-{suffix}"
    package = f"INTEL-PACKAGE-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="Texas Instruments",
            category=category,
            package=package,
        )

        await ComponentRepository.create(
            session,
            mpn=alternative_mpn,
            manufacturer="STMicroelectronics",
            category=category,
            package=package,
        )

        await session.commit()

        source_id = source.id

    intelligence_service = AsyncMock()

    intelligence_service.analyze.return_value = (
        make_intelligence(
            mpn=alternative_mpn,
            manufacturer="STMicroelectronics",
            lifecycle_status=LifecycleStatus.EOL,
            availability=0,
        )
    )

    source_enrichment = ComponentEnrichmentResult(
        mpn=source_mpn,
        manufacturer="Texas Instruments",
        category=category,
        package=package,
        source="test",
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

        print(
            "ANALYZE CALLS:",
            intelligence_service.analyze.await_args_list,
        )

        assert len(analysis.candidates) == 1

        candidate = analysis.candidates[0]

        assert candidate.lifecycle_score == 0.0
        assert candidate.availability_score == 0.0

        assert candidate.compatibility_score == 65.0