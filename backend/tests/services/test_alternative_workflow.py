import json
import uuid

import pytest
from sqlalchemy import delete, select

from backend.app.db.repositories import ComponentRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.models.alternative import AlternativeRecord
from backend.app.models.component import Component
from backend.app.services.alternative_workflow import (
    AlternativeWorkflowService,
)


@pytest.mark.asyncio
async def test_analyze_and_persist_alternatives():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"WORKFLOW-SOURCE-{suffix}"
    alternative_mpn = f"WORKFLOW-ALT-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="Texas Instruments",
            category=f"Analog-{suffix}",
            package=f"PKG-{suffix}",
        )

        alternative = await ComponentRepository.create(
            session,
            mpn=alternative_mpn,
            manufacturer="STMicroelectronics",
            category=f"Analog-{suffix}",
            package=f"PKG-{suffix}",
        )

        await session.commit()

        source_id = source.id
        alternative_id = alternative.id

    source_enrichment = ComponentEnrichmentResult(
        mpn=source_mpn,
        manufacturer="Texas Instruments",
        category=f"Analog-{suffix}",
        package=f"PKG-{suffix}",
        lifecycle_status="ACTIVE",
        availability=5000,
        source="test",
    )

    async with AsyncSessionLocal() as session:
        analysis, persisted_count = (
            await AlternativeWorkflowService
            .analyze_and_persist(
                session,
                component_id=source_id,
                source_enrichment=source_enrichment,
                limit=10,
            )
        )

        await session.commit()

        assert analysis.source_mpn == source_mpn

        assert len(analysis.candidates) == 1

        assert (
            analysis.candidates[0]
            .component.mpn
            == alternative_mpn
        )

        assert (
            analysis.candidates[0]
            .compatibility_score
            == 65.0
        )

        assert (
            analysis.best_candidate
            is not None
        )

        assert (
            analysis.best_candidate
            .component.mpn
            == alternative_mpn
        )

        assert persisted_count == 1

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AlternativeRecord).where(
                AlternativeRecord.source_component_id
                == source_id
            )
        )

        records = list(result.scalars().all())

        assert len(records) == 1

        record = records[0]

        assert (
            record.source_component_id
            == source_id
        )

        assert (
            record.alternative_component_id
            == alternative_id
        )

        assert (
            record.compatibility_score
            == 65.0
        )

        assert record.category_match is True
        assert record.package_match is True
        assert record.manufacturer_match is False

        assert record.lifecycle_score == 0.0
        assert record.availability_score == 0.0

        assert record.reasons is not None

        reasons = json.loads(
            record.reasons
        )

        assert len(reasons) == 6

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id.in_(
                    [source_id, alternative_id]
                )
            )
        )

        await session.commit()