import json
import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    AlternativeRepository,
    ComponentRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.component import Component


@pytest.mark.asyncio
async def test_create_and_retrieve_alternative_record():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=f"ALT-SOURCE-{suffix}",
            manufacturer="Texas Instruments",
            category="Analog IC",
            package="SOIC-8",
        )

        alternative = await ComponentRepository.create(
            session,
            mpn=f"ALT-CANDIDATE-{suffix}",
            manufacturer="STMicroelectronics",
            category="Analog IC",
            package="SOIC-8",
        )

        await session.commit()

        source_id = source.id
        alternative_id = alternative.id

    async with AsyncSessionLocal() as session:
        record = await AlternativeRepository.create(
            session,
            source_component_id=source_id,
            alternative_component_id=alternative_id,
            compatibility_score=75.0,
            category_match=True,
            package_match=True,
            manufacturer_match=False,
            lifecycle_score=15.0,
            availability_score=10.0,
            reasons=[
                "Category is compatible.",
                "Package is compatible.",
                "Manufacturer differs from the source component.",
            ],
        )

        await session.commit()

        record_id = record.id

    async with AsyncSessionLocal() as session:
        retrieved = await AlternativeRepository.get_by_id(
            session,
            record_id,
        )

        assert retrieved is not None
        assert retrieved.id == record_id
        assert retrieved.source_component_id == source_id
        assert retrieved.alternative_component_id == alternative_id
        assert retrieved.compatibility_score == 75.0
        assert retrieved.category_match is True
        assert retrieved.package_match is True
        assert retrieved.manufacturer_match is False
        assert retrieved.lifecycle_score == 15.0
        assert retrieved.availability_score == 10.0

        assert retrieved.reasons is not None

        reasons = json.loads(retrieved.reasons)

        assert reasons == [
            "Category is compatible.",
            "Package is compatible.",
            "Manufacturer differs from the source component.",
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
async def test_list_alternative_history_for_source_component():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=f"ALT-HISTORY-SOURCE-{suffix}",
            manufacturer="Texas Instruments",
            category="Analog IC",
            package="SOIC-8",
        )

        alternative_1 = await ComponentRepository.create(
            session,
            mpn=f"ALT-HISTORY-1-{suffix}",
            manufacturer="STMicroelectronics",
            category="Analog IC",
            package="SOIC-8",
        )

        alternative_2 = await ComponentRepository.create(
            session,
            mpn=f"ALT-HISTORY-2-{suffix}",
            manufacturer="NXP",
            category="Analog IC",
            package="SOIC-8",
        )

        await session.commit()

        source_id = source.id
        alternative_1_id = alternative_1.id
        alternative_2_id = alternative_2.id

    async with AsyncSessionLocal() as session:
        await AlternativeRepository.create(
            session,
            source_component_id=source_id,
            alternative_component_id=alternative_1_id,
            compatibility_score=75.0,
            category_match=True,
            package_match=True,
            manufacturer_match=False,
            lifecycle_score=15.0,
            availability_score=10.0,
        )

        await AlternativeRepository.create(
            session,
            source_component_id=source_id,
            alternative_component_id=alternative_2_id,
            compatibility_score=65.0,
            category_match=True,
            package_match=True,
            manufacturer_match=False,
            lifecycle_score=5.0,
            availability_score=5.0,
        )

        await session.commit()

    async with AsyncSessionLocal() as session:
        records = (
            await AlternativeRepository
            .list_for_source_component(
                session,
                source_id,
            )
        )

        assert len(records) == 2

        assert records[0].source_component_id == source_id
        assert (
            records[0].alternative_component_id
            == alternative_1_id
        )

        assert records[1].source_component_id == source_id
        assert (
            records[1].alternative_component_id
            == alternative_2_id
        )

        assert records[0].compatibility_score == 75.0
        assert records[1].compatibility_score == 65.0

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id.in_(
                    [
                        source_id,
                        alternative_1_id,
                        alternative_2_id,
                    ]
                )
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_alternative_repository_handles_empty_history():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"ALT-EMPTY-{suffix}",
            manufacturer="Test Manufacturer",
            category="Analog IC",
            package="SOIC-8",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        records = (
            await AlternativeRepository
            .list_for_source_component(
                session,
                component_id,
            )
        )

        assert records == []

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )
        await session.commit()