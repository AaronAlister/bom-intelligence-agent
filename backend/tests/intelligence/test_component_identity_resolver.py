import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.component_identity import (
    ComponentIdentityResolver,
)
from backend.app.models.component import Component


@pytest.mark.asyncio
async def test_resolver_creates_new_component():
    suffix = uuid.uuid4().hex[:8]
    mpn = f"RESOLVER-NEW-{suffix}"

    async with AsyncSessionLocal() as session:
        component = await ComponentIdentityResolver.resolve(
            session,
            mpn=f"  {mpn}  ",
            manufacturer=" Test Manufacturer ",
            description="Test component",
            category="IC",
            package="QFN",
        )

        await session.commit()

        assert component.id is not None
        assert component.mpn == mpn
        assert component.normalized_mpn == mpn
        assert component.normalized_manufacturer == "Test Manufacturer"

        component_id = component.id

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(Component.id == component_id)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_resolver_reuses_existing_component():
    suffix = uuid.uuid4().hex[:8]
    mpn = f"RESOLVER-EXISTING-{suffix}"

    async with AsyncSessionLocal() as session:
        first = await ComponentIdentityResolver.resolve(
            session,
            mpn=mpn,
            manufacturer="Original Manufacturer",
        )

        await session.commit()

        first_id = first.id

    async with AsyncSessionLocal() as session:
        second = await ComponentIdentityResolver.resolve(
            session,
            mpn=f"  {mpn}  ",
            manufacturer="Different Manufacturer",
        )

        assert second.id == first_id

        await session.execute(
            delete(Component).where(Component.id == first_id)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_resolver_rejects_missing_mpn():
    async with AsyncSessionLocal() as session:
        with pytest.raises(ValueError, match="MPN is required"):
            await ComponentIdentityResolver.resolve(
                session,
                mpn=None,
                manufacturer="Test Manufacturer",
            )