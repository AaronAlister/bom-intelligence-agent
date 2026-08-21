import uuid

import pytest
from sqlalchemy import delete, func, select

from backend.app.db.session import AsyncSessionLocal
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component
from backend.app.models.ingestion import IngestionRecord
from backend.app.services import BOMPersistenceService


@pytest.mark.asyncio
async def test_persist_bom_creates_complete_bom_graph():
    suffix = uuid.uuid4().hex[:8]

    bom_identifier = f"PERSIST-TEST-BOM-{suffix}"

    components = [
        {
            "mpn": f"RES-001-{suffix}",
            "manufacturer": "Test Manufacturer",
            "description": "Test resistor",
            "category": "Resistor",
            "package": "0603",
            "quantity": 2,
            "reference_designators": "R1,R2",
        },
        {
            "mpn": f"CAP-001-{suffix}",
            "manufacturer": "Test Manufacturer",
            "description": "Test capacitor",
            "category": "Capacitor",
            "package": "0603",
            "quantity": 1,
            "reference_designators": "C1",
        },
        {
            "mpn": f"IC-001-{suffix}",
            "manufacturer": "Test Manufacturer",
            "description": "Test IC",
            "category": "Integrated Circuit",
            "package": "QFN",
            "quantity": 1,
            "reference_designators": "U1",
        },
    ]

    async with AsyncSessionLocal() as session:
        bom, ingestion = await BOMPersistenceService.persist_bom(
            session,
            bom_id=bom_identifier,
            product="Persistence Test Product",
            revision="1.0",
            source_file="persistence-test.xlsx",
            source_format="xlsx",
            components=components,
        )

        await session.commit()

        bom_db_id = bom.id
        ingestion_id = ingestion.id

    async with AsyncSessionLocal() as session:
        stored_bom = await session.scalar(
            select(BOM).where(BOM.id == bom_db_id)
        )

        assert stored_bom is not None
        assert stored_bom.bom_id == bom_identifier

        component_count = await session.scalar(
            select(func.count())
            .select_from(Component)
            .where(
                Component.mpn.in_(
                    [component["mpn"] for component in components]
                )
            )
        )

        assert component_count == 3

        mapping_count = await session.scalar(
            select(func.count())
            .select_from(BOMComponent)
            .where(BOMComponent.bom_id == bom_db_id)
        )

        assert mapping_count == 3

        stored_ingestion = await session.scalar(
            select(IngestionRecord).where(
                IngestionRecord.id == ingestion_id
            )
        )

        assert stored_ingestion is not None
        assert stored_ingestion.bom_id == bom_db_id
        assert stored_ingestion.status == "success"
        assert stored_ingestion.row_count == 3
        assert stored_ingestion.error_count == 0

        await session.execute(
            delete(BOM).where(BOM.id == bom_db_id)
        )
        await session.commit()

@pytest.mark.asyncio
async def test_persist_bom_reuses_existing_component():
    suffix = uuid.uuid4().hex[:8]

    shared_mpn = f"SHARED-MPN-{suffix}"
    bom_a_identifier = f"REUSE-BOM-A-{suffix}"
    bom_b_identifier = f"REUSE-BOM-B-{suffix}"

    component_data = {
        "mpn": shared_mpn,
        "manufacturer": "Shared Manufacturer",
        "description": "Shared component",
        "category": "Integrated Circuit",
        "package": "QFN",
        "quantity": 1,
        "reference_designators": "U1",
    }

    async with AsyncSessionLocal() as session:
        bom_a, _ = await BOMPersistenceService.persist_bom(
            session,
            bom_id=bom_a_identifier,
            product="Reuse Test Product A",
            revision="1.0",
            source_file="reuse-a.xlsx",
            source_format="xlsx",
            components=[component_data],
        )

        await session.commit()

        bom_a_id = bom_a.id

    async with AsyncSessionLocal() as session:
        bom_b, _ = await BOMPersistenceService.persist_bom(
            session,
            bom_id=bom_b_identifier,
            product="Reuse Test Product B",
            revision="1.0",
            source_file="reuse-b.xlsx",
            source_format="xlsx",
            components=[component_data],
        )

        await session.commit()

        bom_b_id = bom_b.id

    async with AsyncSessionLocal() as session:
        matching_components = await session.scalars(
            select(Component).where(
                Component.mpn == shared_mpn
            )
        )

        components = list(matching_components)

        assert len(components) == 1

        component_id = components[0].id

        mappings = await session.scalars(
            select(BOMComponent).where(
                BOMComponent.component_id == component_id
            )
        )

        mappings = list(mappings)

        assert len(mappings) == 2

        assert {
            mapping.bom_id
            for mapping in mappings
        } == {
            bom_a_id,
            bom_b_id,
        }

        await session.execute(
            delete(BOM).where(
                BOM.id.in_([bom_a_id, bom_b_id])
            )
        )
        await session.commit()

@pytest.mark.asyncio
async def test_persist_bom_rolls_back_on_failure():
    suffix = uuid.uuid4().hex[:8]

    bom_identifier = f"ROLLBACK-BOM-{suffix}"
    mpn = f"ROLLBACK-MPN-{suffix}"

    components = [
        {
            "mpn": mpn,
            "manufacturer": "Rollback Manufacturer",
            "quantity": 1,
            "reference_designators": "U1",
        },
        {
            "mpn": mpn,
            "manufacturer": "Rollback Manufacturer",
            "quantity": 1,
            "reference_designators": "U2",
        },
    ]

    async with AsyncSessionLocal() as session:
        with pytest.raises(Exception):
            await BOMPersistenceService.persist_bom(
                session,
                bom_id=bom_identifier,
                product="Rollback Test",
                revision="1.0",
                source_file="rollback-test.xlsx",
                source_format="xlsx",
                components=components,
            )

        await session.rollback()

    async with AsyncSessionLocal() as session:
        stored_bom = await session.scalar(
            select(BOM).where(
                BOM.bom_id == bom_identifier
            )
        )

        stored_component = await session.scalar(
            select(Component).where(
                Component.mpn == mpn
            )
        )

        assert stored_bom is None
        assert stored_component is None