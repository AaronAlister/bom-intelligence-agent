import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    BOMRepository,
    BOMRiskRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.bom import BOM
from backend.app.models.bom_risk import BOMRiskRecord


@pytest.mark.asyncio
async def test_create_and_retrieve_bom_risk_record():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"REPO-BOM-RISK-{suffix}",
            product="Repository Test",
            revision="1.0",
        )

        await session.commit()

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        record = await BOMRiskRepository.create(
            session,
            bom_id=bom_id,
            overall_score=72.5,
            severity="HIGH",
            component_count=25,
            high_risk_count=5,
            critical_count=2,
            lifecycle_risk_count=3,
            availability_risk_count=4,
        )

        await session.commit()

        risk_id = record.id

    async with AsyncSessionLocal() as session:
        result = await BOMRiskRepository.get_by_id(
            session,
            risk_id,
        )

        assert result is not None
        assert result.id == risk_id
        assert result.bom_id == bom_id
        assert result.overall_score == 72.5
        assert result.severity == "HIGH"
        assert result.component_count == 25
        assert result.high_risk_count == 5
        assert result.critical_count == 2
        assert result.lifecycle_risk_count == 3
        assert result.availability_risk_count == 4

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOMRiskRecord).where(
                BOMRiskRecord.id == risk_id
            )
        )
        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_list_for_bom_returns_historical_records():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"HISTORY-BOM-{suffix}",
        )

        await session.commit()

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        first = await BOMRiskRepository.create(
            session,
            bom_id=bom_id,
            overall_score=80.0,
            severity="CRITICAL",
            component_count=10,
            high_risk_count=4,
            critical_count=2,
            lifecycle_risk_count=3,
            availability_risk_count=2,
        )

        second = await BOMRiskRepository.create(
            session,
            bom_id=bom_id,
            overall_score=45.0,
            severity="MEDIUM",
            component_count=10,
            high_risk_count=2,
            critical_count=0,
            lifecycle_risk_count=1,
            availability_risk_count=1,
        )

        await session.commit()

        first_id = first.id
        second_id = second.id

    async with AsyncSessionLocal() as session:
        records = await BOMRiskRepository.list_for_bom(
            session,
            bom_id,
        )

        assert len(records) == 2

        assert records[0].id == first_id
        assert records[1].id == second_id

        assert records[0].overall_score == 80.0
        assert records[1].overall_score == 45.0

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


@pytest.mark.asyncio
async def test_bom_risk_repository_persists_json_details():
    suffix = uuid.uuid4().hex[:8]

    details = {
        "top_risk_components": [
            {
                "component_id": 101,
                "mpn": "LM358",
                "score": 92.5,
                "severity": "CRITICAL",
            },
            {
                "component_id": 102,
                "mpn": "TPS62160",
                "score": 78.0,
                "severity": "HIGH",
            },
        ],
        "recommendations": [
            "Review critical components",
            "Evaluate alternate suppliers",
        ],
    }

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"DETAILS-BOM-{suffix}",
        )

        await session.commit()

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        record = await BOMRiskRepository.create(
            session,
            bom_id=bom_id,
            overall_score=85.25,
            severity="CRITICAL",
            component_count=50,
            high_risk_count=8,
            critical_count=3,
            lifecycle_risk_count=4,
            availability_risk_count=6,
            details=details,
        )

        await session.commit()

        risk_id = record.id

    async with AsyncSessionLocal() as session:
        result = await BOMRiskRepository.get_by_id(
            session,
            risk_id,
        )

        assert result is not None
        assert result.details is not None

        import json

        stored_details = json.loads(
            result.details
        )

        assert (
            stored_details["top_risk_components"][0]["mpn"]
            == "LM358"
        )

        assert (
            stored_details["top_risk_components"][0]["score"]
            == 92.5
        )

        assert (
            stored_details["recommendations"][0]
            == "Review critical components"
        )

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOMRiskRecord).where(
                BOMRiskRecord.id == risk_id
            )
        )
        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id
            )
        )
        await session.commit()