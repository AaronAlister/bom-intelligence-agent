import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.app.db.repositories import BOMRepository, RiskRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.bom import BOM
from backend.app.models.component import Component


BASE_URL = "http://test"


@pytest.mark.asyncio
async def test_bom_risk_returns_404_for_unknown_bom():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.get(
            "/api/v1/boms/999999999/risk"
        )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "BOM 999999999 not found."
    )


@pytest.mark.asyncio
async def test_bom_risk_returns_unknown_for_unassessed_bom():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"API-EMPTY-{suffix}",
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
                f"/api/v1/boms/{bom_id}/risk"
            )

        assert response.status_code == 200

        data = response.json()

        assert data["bom_id"] == bom_id
        assert data["overall_score"] == 0.0
        assert data["severity"] == "UNKNOWN"

        assert data["component_count"] == 0
        assert data["high_risk_count"] == 0
        assert data["critical_count"] == 0

        assert data["top_risk_components"] == []
        assert data["risk_drivers"] == []

        assert len(data["recommendations"]) == 1

        assert (
            data["recommendations"][0]["priority"]
            == "UNKNOWN"
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
async def test_bom_risk_returns_risk_intelligence():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"API-RISK-{suffix}",
        )

        component = Component(
            mpn=f"API-RISK-COMP-{suffix}",
            manufacturer="Test Manufacturer",
        )

        session.add(component)

        await session.flush()

        await RiskRepository.create(
            session,
            component_id=component.id,
            risk_type="COMPONENT",
            score=95.0,
            severity="CRITICAL",
            details={
                "lifecycle_score": 100.0,
                "availability_score": 80.0,
                "reasons": [
                    "Component is obsolete.",
                    "No distributor stock.",
                ],
            },
        )

        from backend.app.models.bom_component import (
            BOMComponent,
        )

        session.add(
            BOMComponent(
                bom_id=bom.id,
                component_id=component.id,
                quantity=2,
            )
        )

        await session.commit()

        bom_id = bom.id
        component_id = component.id

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.get(
                f"/api/v1/boms/{bom_id}/risk"
            )

        assert response.status_code == 200

        data = response.json()

        assert data["bom_id"] == bom_id

        assert data["overall_score"] == 95.0
        assert data["severity"] == "CRITICAL"

        assert data["component_count"] == 1
        assert data["high_risk_count"] == 1
        assert data["critical_count"] == 1

        assert data["lifecycle_risk_count"] == 1
        assert data["availability_risk_count"] == 1

        assert len(
            data["top_risk_components"]
        ) == 1

        component_data = (
            data["top_risk_components"][0]
        )

        assert (
            component_data["component_id"]
            == component_id
        )

        assert (
            component_data["mpn"]
            == f"API-RISK-COMP-{suffix}"
        )

        assert component_data["quantity"] == 2
        assert component_data["score"] == 95.0
        assert component_data["severity"] == "CRITICAL"

        assert (
            component_data["lifecycle_risk"]
            is True
        )

        assert (
            component_data["availability_risk"]
            is True
        )

        assert data["summary"] != ""

        assert len(
            data["risk_drivers"]
        ) == 1

        driver = data["risk_drivers"][0]

        assert (
            driver["component_id"]
            == component_id
        )

        assert (
            driver["mpn"]
            == f"API-RISK-COMP-{suffix}"
        )

        assert (
            driver["severity"]
            == "CRITICAL"
        )

        assert driver["reason"] != ""

        assert len(
            data["recommendations"]
        ) >= 1

        component_recommendations = [
            recommendation
            for recommendation
            in data["recommendations"]
            if recommendation["component_id"]
            == component_id
        ]

        assert len(
            component_recommendations
        ) == 1

        recommendation = (
            component_recommendations[0]
        )

        assert (
            recommendation["priority"]
            == "CRITICAL"
        )

        assert recommendation["action"] != ""
        assert recommendation["reason"] != ""

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BOM).where(
                    BOM.id == bom_id
                )
            )

            await session.execute(
                delete(Component).where(
                    Component.id == component_id
                )
            )

            await session.commit()