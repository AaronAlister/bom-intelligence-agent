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
async def test_list_for_bom_returns_historical_records():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"HISTORY-{suffix}",
        )

        await session.flush()

        first = await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=20.0,
            severity="LOW",
            component_count=5,
            high_risk_count=0,
            critical_count=0,
            lifecycle_risk_count=0,
            availability_risk_count=0,
        )

        second = await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=60.0,
            severity="HIGH",
            component_count=5,
            high_risk_count=2,
            critical_count=0,
            lifecycle_risk_count=1,
            availability_risk_count=1,
        )

        third = await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=85.0,
            severity="CRITICAL",
            component_count=5,
            high_risk_count=3,
            critical_count=2,
            lifecycle_risk_count=2,
            availability_risk_count=2,
        )

        await session.commit()

        records = await BOMRiskRepository.list_for_bom(
            session,
            bom.id,
        )

        assert len(records) == 3

        assert records[0].id == first.id
        assert records[1].id == second.id
        assert records[2].id == third.id

        assert records[0].overall_score == 20.0
        assert records[1].overall_score == 60.0
        assert records[2].overall_score == 85.0

        bom_id = bom.id

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
async def test_get_latest_for_bom_returns_latest_snapshot():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"LATEST-{suffix}",
        )

        await session.flush()

        first = await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=35.0,
            severity="MEDIUM",
            component_count=4,
            high_risk_count=1,
            critical_count=0,
            lifecycle_risk_count=1,
            availability_risk_count=0,
        )

        second = await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=75.0,
            severity="CRITICAL",
            component_count=4,
            high_risk_count=2,
            critical_count=1,
            lifecycle_risk_count=2,
            availability_risk_count=1,
        )

        await session.commit()

        latest = (
            await BOMRiskRepository.get_latest_for_bom(
                session,
                bom.id,
            )
        )

        assert latest is not None
        assert latest.id == second.id
        assert latest.id != first.id
        assert latest.overall_score == 75.0
        assert latest.severity == "CRITICAL"

        bom_id = bom.id

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
async def test_get_latest_for_bom_returns_none_when_no_history():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"NO-HISTORY-{suffix}",
        )

        await session.commit()

        result = (
            await BOMRiskRepository.get_latest_for_bom(
                session,
                bom.id,
            )
        )

        assert result is None

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id
            )
        )

        await session.commit()