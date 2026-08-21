import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component
from backend.app.api.intelligence_routes import (
    get_bom_intelligence_service,
)


BASE_URL = "http://test"


@pytest.mark.asyncio
async def test_bom_intelligence_returns_404_for_unknown_bom():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/999999999/intelligence"
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "BOM 999999999 not found."
    )


# FIXED: use bom.bom_id (UUID) instead of bom.id
@pytest.mark.asyncio
async def test_bom_intelligence_rejects_empty_bom():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=f"API-INTEL-{suffix}",
        )

        session.add(bom)

        await session.commit()

        bom_id = bom.bom_id  # use the UUID string

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                f"/api/v1/boms/{bom_id}/intelligence"
            )

        assert response.status_code == 422

        assert (
            response.json()["detail"]
            == f"BOM {bom_id} contains no components."
        )

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BOM).where(
                    BOM.bom_id == bom_id
                )
            )

            await session.commit()