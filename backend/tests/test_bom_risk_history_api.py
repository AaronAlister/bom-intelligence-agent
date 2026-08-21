import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.app.db.repositories import (
    BOMRepository,
    BOMRiskRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.bom import BOM
from backend.app.models.bom_risk import BOMRiskRecord


BASE_URL = "http://test"


@pytest.mark.asyncio
async def test_bom_risk_history_returns_404_for_unknown_bom():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.get(
            "/api/v1/boms/999999999/risk/history"
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "BOM 999999999 not found."
    )


@pytest.mark.asyncio
async def test_bom_risk_history_returns_unknown_for_no_history():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"API-NO-HISTORY-{suffix}",
        )

        await session.commit()

        bom_id = bom.id

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.get(
                f"/api/v1/boms/{bom_id}/risk/history"
            )

        assert response.status_code == 200

        data = response.json()

        assert data["bom_id"] == bom_id
        assert data["snapshot_count"] == 0
        assert data["history"] == []

        assert data["trend"]["trend"] == "UNKNOWN"
        assert data["trend"]["snapshot_count"] == 0

        assert (
            data["trend"]["previous_score"]
            is None
        )

        assert (
            data["trend"]["current_score"]
            is None
        )

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BOM).where(
                    BOM.id == bom_id
                )
            )

            await session.commit()


@pytest.mark.asyncio
async def test_bom_risk_history_returns_worsening_trend():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"API-HISTORY-{suffix}",
        )

        await session.flush()

        await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=20.0,
            severity="LOW",
            component_count=10,
            high_risk_count=0,
            critical_count=0,
            lifecycle_risk_count=0,
            availability_risk_count=0,
        )

        await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=60.0,
            severity="HIGH",
            component_count=10,
            high_risk_count=3,
            critical_count=1,
            lifecycle_risk_count=2,
            availability_risk_count=1,
        )

        await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=85.0,
            severity="CRITICAL",
            component_count=10,
            high_risk_count=4,
            critical_count=2,
            lifecycle_risk_count=3,
            availability_risk_count=2,
        )

        await session.commit()

        bom_id = bom.id

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.get(
                f"/api/v1/boms/{bom_id}/risk/history"
            )

        assert response.status_code == 200

        data = response.json()

        assert data["bom_id"] == bom_id
        assert data["snapshot_count"] == 3

        assert len(data["history"]) == 3

        assert (
            data["history"][0]["overall_score"]
            == 20.0
        )

        assert (
            data["history"][1]["overall_score"]
            == 60.0
        )

        assert (
            data["history"][2]["overall_score"]
            == 85.0
        )

        trend = data["trend"]

        assert trend["trend"] == "WORSENING"
        assert trend["snapshot_count"] == 3

        assert trend["previous_score"] == 60.0
        assert trend["current_score"] == 85.0
        assert trend["score_change"] == 25.0

        assert (
            trend["previous_severity"]
            == "HIGH"
        )

        assert (
            trend["current_severity"]
            == "CRITICAL"
        )

        assert (
            trend["high_risk_count_change"]
            == 1
        )

        assert (
            trend["critical_count_change"]
            == 1
        )

        assert (
            trend["lifecycle_risk_count_change"]
            == 1
        )

        assert (
            trend["availability_risk_count_change"]
            == 1
        )

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BOMRiskRecord).where(
                    BOMRiskRecord.bom_id == bom_id
                )
            )

            await session.execute(
                delete(BOM).where(
                    BOM.id == bom_id
                )
            )

            await session.commit()