import json
import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import ComponentRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.alternatives.models import (
    AlternativeAnalysis,
    AlternativeCandidate,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.models.component import Component
from backend.app.services.alternative_persistence import (
    AlternativePersistenceService,
)


@pytest.mark.asyncio
async def test_persist_alternative_analysis():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"PERSIST-SOURCE-{suffix}"
    alternative_mpn = f"PERSIST-ALT-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="Texas Instruments",
            category="Analog IC",
            package="SOIC-8",
        )

        alternative = await ComponentRepository.create(
            session,
            mpn=alternative_mpn,
            manufacturer="STMicroelectronics",
            category="Analog IC",
            package="SOIC-8",
        )

        await session.commit()

        source_id = source.id
        alternative_id = alternative.id

    candidate = AlternativeCandidate(
        component=ComponentEnrichmentResult(
            mpn=alternative_mpn,
            manufacturer="STMicroelectronics",
            category="Analog IC",
            package="SOIC-8",
            lifecycle_status="ACTIVE",
            availability=5000,
            source="test",
        ),
        compatibility_score=75.0,
        category_match=True,
        package_match=True,
        manufacturer_match=False,
        lifecycle_score=15.0,
        availability_score=10.0,
        reasons=[
            "Category is compatible.",
            "Package is compatible.",
        ],
    )

    analysis = AlternativeAnalysis(
        source_mpn=source_mpn,
        candidates=[candidate],
        best_candidate=candidate,
    )

    async with AsyncSessionLocal() as session:
        records = (
            await AlternativePersistenceService
            .persist_analysis(
                session,
                source_component_id=source_id,
                analysis=analysis,
            )
        )

        await session.commit()

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

        assert record.compatibility_score == 75.0
        assert record.category_match is True
        assert record.package_match is True
        assert record.manufacturer_match is False
        assert record.lifecycle_score == 15.0
        assert record.availability_score == 10.0

        assert record.reasons is not None

        reasons = json.loads(record.reasons)

        assert reasons == [
            "Category is compatible.",
            "Package is compatible.",
        ]

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id.in_(
                    [source_id, alternative_id]
                )
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_persist_skips_unknown_candidate():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"PERSIST-UNKNOWN-SOURCE-{suffix}"
    unknown_mpn = f"UNKNOWN-ALT-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="Texas Instruments",
            category="Analog IC",
            package="SOIC-8",
        )

        await session.commit()

        source_id = source.id

    candidate = AlternativeCandidate(
        component=ComponentEnrichmentResult(
            mpn=unknown_mpn,
            manufacturer="Unknown",
            category="Analog IC",
            package="SOIC-8",
            lifecycle_status="ACTIVE",
            availability=1000,
            source="test",
        ),
        compatibility_score=75.0,
        category_match=True,
        package_match=True,
        manufacturer_match=False,
        lifecycle_score=15.0,
        availability_score=10.0,
        reasons=[
            "Candidate not present in component catalog."
        ],
    )

    analysis = AlternativeAnalysis(
        source_mpn=source_mpn,
        candidates=[candidate],
        best_candidate=candidate,
    )

    async with AsyncSessionLocal() as session:
        records = (
            await AlternativePersistenceService
            .persist_analysis(
                session,
                source_component_id=source_id,
                analysis=analysis,
            )
        )

        await session.commit()

        assert records == []

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == source_id
            )
        )
        await session.commit()