import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    BOMRepository,
    ComponentRepository,
    IngestionRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.bom import BOM
from backend.app.models.component import Component
from sqlalchemy.exc import IntegrityError

@pytest.mark.asyncio
async def test_bom_repository_create_and_get():
    suffix = uuid.uuid4().hex[:8]

    bom_identifier = f"REPO-TEST-BOM-{suffix}"

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=bom_identifier,
            product="Repository Test Product",
            revision="1.0",
            source_file="repository-test.csv",
        )

        await session.commit()

        bom_db_id = bom.id

    async with AsyncSessionLocal() as session:
        fetched_by_id = await BOMRepository.get_by_id(
            session,
            bom_db_id,
        )

        assert fetched_by_id is not None
        assert fetched_by_id.bom_id == bom_identifier
        assert fetched_by_id.product == "Repository Test Product"
        assert fetched_by_id.revision == "1.0"

        fetched_by_identifier = await BOMRepository.get_by_bom_id(
            session,
            bom_identifier,
        )

        assert fetched_by_identifier is not None
        assert fetched_by_identifier.id == bom_db_id

        await session.execute(
            delete(BOM).where(BOM.id == bom_db_id)
        )
        await session.commit()

@pytest.mark.asyncio
async def test_component_repository_create_and_get():
    suffix = uuid.uuid4().hex[:8]

    mpn = f"REPO-TEST-MPN-{suffix}"

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=mpn,
            manufacturer="Repository Test Manufacturer",
            description="Repository test component",
            category="Test",
            package="QFN",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        fetched_by_id = await ComponentRepository.get_by_id(
            session,
            component_id,
        )

        assert fetched_by_id is not None
        assert fetched_by_id.mpn == mpn
        assert fetched_by_id.manufacturer == "Repository Test Manufacturer"
        assert fetched_by_id.package == "QFN"

        fetched_by_mpn = await ComponentRepository.get_by_mpn(
            session,
            mpn,
        )

        assert fetched_by_mpn is not None
        assert fetched_by_mpn.id == component_id

        await session.execute(
            delete(Component).where(Component.id == component_id)
        )
        await session.commit()

@pytest.mark.asyncio
async def test_ingestion_repository_create_and_get():
    suffix = uuid.uuid4().hex[:8]

    bom_identifier = f"REPO-INGEST-BOM-{suffix}"

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=bom_identifier,
            product="Ingestion Repository Test",
            revision="1.0",
            source_file="ingestion-test.xlsx",
        )

        await session.flush()

        record = await IngestionRepository.create(
            session,
            bom_id=bom.id,
            source_file="ingestion-test.xlsx",
            source_format="xlsx",
            status="success",
            row_count=25,
            error_count=0,
        )

        await session.commit()

        bom_db_id = bom.id
        ingestion_id = record.id

    async with AsyncSessionLocal() as session:
        fetched = await IngestionRepository.get_by_id(
            session,
            ingestion_id,
        )

        assert fetched is not None
        assert fetched.bom_id == bom_db_id
        assert fetched.source_file == "ingestion-test.xlsx"
        assert fetched.source_format == "xlsx"
        assert fetched.status == "success"
        assert fetched.row_count == 25
        assert fetched.error_count == 0

        records = await IngestionRepository.list_for_bom(
            session,
            bom_db_id,
        )

        assert len(records) == 1
        assert records[0].id == ingestion_id

        await session.execute(
            delete(BOM).where(BOM.id == bom_db_id)
        )
        await session.commit()

@pytest.mark.asyncio
async def test_component_repository_rejects_duplicate_mpn():
    suffix = uuid.uuid4().hex[:8]
    mpn = f"REPO-DUPLICATE-MPN-{suffix}"

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=mpn,
            manufacturer="First Manufacturer",
        )

        await session.commit()
        component_id = component.id

    async with AsyncSessionLocal() as session:
        with pytest.raises(IntegrityError):
            await ComponentRepository.create(
                session,
                mpn=mpn,
                manufacturer="Second Manufacturer",
            )

        await session.rollback()

    async with AsyncSessionLocal() as session:
        components = await ComponentRepository.list_all(session)

        matching = [
            component
            for component in components
            if component.mpn == mpn
        ]

        assert len(matching) == 1
        assert matching[0].id == component_id

        await session.execute(
            delete(Component).where(Component.id == component_id)
        )
        await session.commit()

@pytest.mark.asyncio
async def test_component_repository_get_by_normalized_mpn():
    suffix = uuid.uuid4().hex[:8]

    mpn = f"REPO-NORMALIZED-MPN-{suffix}"
    normalized_mpn = mpn.strip()

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=mpn,
            manufacturer="Normalized Test Manufacturer",
        )

        component.normalized_mpn = normalized_mpn

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        fetched = await ComponentRepository.get_by_normalized_mpn(
            session,
            normalized_mpn,
        )

        assert fetched is not None
        assert fetched.id == component_id
        assert fetched.mpn == mpn

        await session.execute(
            delete(Component).where(Component.id == component_id)
        )
        await session.commit()