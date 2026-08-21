import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from backend.app.db.session import AsyncSessionLocal, engine
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component


@pytest.fixture(autouse=True)
async def dispose_engine():
    await engine.dispose()
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_deleting_bom_cascades_to_bom_components():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"CASCADE-TEST-BOM-{suffix}",
            product="Cascade Test Product",
            revision="1.0",
            source_file="cascade-test.csv",
        )

        component = Component(
            mpn=f"CASCADE-TEST-COMPONENT-{suffix}",
            manufacturer="Test Manufacturer",
        )

        session.add_all([bom, component])
        await session.flush()

        association = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=2,
            reference_designators="R1,R2",
        )

        session.add(association)
        await session.commit()

        bom_id = bom.id
        association_id = association.id
        component_id = component.id

        await session.execute(
            delete(BOM).where(BOM.id == bom_id)
        )
        await session.commit()

    async with AsyncSessionLocal() as verify_session:
        remaining_association = await verify_session.scalar(
            select(BOMComponent).where(
                BOMComponent.id == association_id
            )
        )

        remaining_component = await verify_session.scalar(
            select(Component).where(
                Component.id == component_id
            )
        )

        assert remaining_association is None
        assert remaining_component is not None


@pytest.mark.asyncio
async def test_deleting_component_is_restricted_when_bom_component_exists():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"RESTRICT-TEST-BOM-{suffix}",
            product="Restrict Test Product",
            revision="1.0",
            source_file="restrict-test.csv",
        )

        component = Component(
            mpn=f"RESTRICT-TEST-COMPONENT-{suffix}",
            manufacturer="Test Manufacturer",
        )

        session.add_all([bom, component])
        await session.flush()

        association = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=1,
            reference_designators="U1",
        )

        session.add(association)
        await session.commit()

        bom_id = bom.id
        component_id = component.id
        association_id = association.id

    async with AsyncSessionLocal() as delete_session:
        with pytest.raises(IntegrityError):
            await delete_session.execute(
                delete(Component).where(
                    Component.id == component_id
                )
            )
            await delete_session.commit()

        await delete_session.rollback()

    async with AsyncSessionLocal() as verify_session:
        remaining_component = await verify_session.scalar(
            select(Component).where(
                Component.id == component_id
            )
        )

        remaining_association = await verify_session.scalar(
            select(BOMComponent).where(
                BOMComponent.id == association_id
            )
        )

        assert remaining_component is not None
        assert remaining_association is not None

        await verify_session.execute(
            delete(BOM).where(BOM.id == bom_id)
        )
        await verify_session.commit()