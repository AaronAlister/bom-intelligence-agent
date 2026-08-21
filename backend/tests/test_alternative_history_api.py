import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.app.db.repositories import (
    AlternativeRepository,
    ComponentRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.component import Component


@pytest.mark.asyncio
async def test_alternative_history_api_returns_persisted_records():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=f"HISTORY-SOURCE-{suffix}",
            manufacturer="Texas Instruments",
            category=f"History-{suffix}",
            package=f"PKG-{suffix}",
        )

        alternative_1 = await ComponentRepository.create(
            session,
            mpn=f"HISTORY-ALT-1-{suffix}",
            manufacturer="STMicroelectronics",
            category=f"History-{suffix}",
            package=f"PKG-{suffix}",
        )

        alternative_2 = await ComponentRepository.create(
            session,
            mpn=f"HISTORY-ALT-2-{suffix}",
            manufacturer="NXP",
            category=f"History-{suffix}",
            package=f"PKG-{suffix}",
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
            compatibility_score=65.0,
            category_match=True,
            package_match=True,
            manufacturer_match=False,
            lifecycle_score=0.0,
            availability_score=0.0,
            reasons=[
                "Category is compatible.",
                "Package is compatible.",
            ],
        )

        await AlternativeRepository.create(
            session,
            source_component_id=source_id,
            alternative_component_id=alternative_2_id,
            compatibility_score=75.0,
            category_match=True,
            package_match=True,
            manufacturer_match=True,
            lifecycle_score=0.0,
            availability_score=0.0,
            reasons=[
                "Category is compatible.",
                "Package is compatible.",
                "Manufacturer matches the source component.",
            ],
        )

        await session.commit()

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/v1/components/"
                f"{source_id}/alternatives/history"
            )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["source_component_id"]
            == source_id
        )

        assert len(data["records"]) == 2

        first = data["records"][0]
        second = data["records"][1]

        # Newest record should appear first.
        assert (
            first["alternative_component_id"]
            == alternative_2_id
        )

        assert (
            first["compatibility_score"]
            == 75.0
        )

        assert first["manufacturer_match"] is True

        assert first["reasons"] == [
            "Category is compatible.",
            "Package is compatible.",
            "Manufacturer matches the source component.",
        ]

        assert (
            second["alternative_component_id"]
            == alternative_1_id
        )

        assert (
            second["compatibility_score"]
            == 65.0
        )

        assert second["manufacturer_match"] is False

        assert "created_at" in first
        assert "created_at" in second

    finally:
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
async def test_alternative_history_api_returns_empty_history():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"HISTORY-EMPTY-{suffix}",
            manufacturer="Test Manufacturer",
            category=f"Empty-{suffix}",
            package=f"PKG-{suffix}",
        )

        await session.commit()

        component_id = component.id

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/v1/components/"
                f"{component_id}/alternatives/history"
            )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["source_component_id"]
            == component_id
        )

        assert data["records"] == []

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(Component).where(
                    Component.id == component_id
                )
            )

            await session.commit()