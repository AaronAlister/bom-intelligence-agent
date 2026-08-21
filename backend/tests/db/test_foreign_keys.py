import pytest
from sqlalchemy import delete
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
async def test_bom_component_requires_existing_bom():
    async with AsyncSessionLocal() as session:
        component = Component(
            mpn="FK-TEST-COMPONENT-001",
            manufacturer="Test Manufacturer",
        )

        session.add(component)
        await session.flush()

        association = BOMComponent(
            bom_id=999999,
            component_id=component.id,
            quantity=1,
        )

        session.add(association)

        with pytest.raises(IntegrityError):
            await session.flush()

        await session.rollback()

        await session.execute(
            delete(Component).where(Component.id == component.id)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_bom_component_requires_existing_component():
    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id="FK-TEST-BOM-001",
            product="Foreign Key Test",
            revision="1.0",
            source_file="fk-test.csv",
        )

        session.add(bom)
        await session.flush()

        association = BOMComponent(
            bom_id=bom.id,
            component_id=999999,
            quantity=1,
        )

        session.add(association)

        with pytest.raises(IntegrityError):
            await session.flush()

        await session.rollback()

        await session.execute(
            delete(BOM).where(BOM.id == bom.id)
        )
        await session.commit()