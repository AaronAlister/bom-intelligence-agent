import json
import uuid

import pytest
from sqlalchemy import delete, select

from backend.app.db.repositories import BOMRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.risk.bom_models import (
    BOMComponentRisk,
    BOMRiskAssessment,
)
from backend.app.intelligence.risk.models import RiskSeverity
from backend.app.models.bom import BOM
from backend.app.models.bom_risk import BOMRiskRecord
from backend.app.services.bom_risk_persistence import (
    BOMRiskPersistenceService,
)


@pytest.mark.asyncio
async def test_persist_bom_risk():
    suffix = uuid.uuid4().hex[:8]

    assessment = BOMRiskAssessment(
        overall_score=72.5,
        severity=RiskSeverity.HIGH,
        component_count=25,
        high_risk_count=5,
        critical_count=2,
        lifecycle_risk_count=3,
        availability_risk_count=4,
        top_risk_components=[
            BOMComponentRisk(
                component_id=101,
                mpn="LM358",
                quantity=10,
                score=92.5,
                severity=RiskSeverity.CRITICAL,
                lifecycle_risk=True,
                availability_risk=True,
            ),
        ],
    )

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"PERSIST-BOM-{suffix}",
        )

        await session.commit()

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        record = (
            await BOMRiskPersistenceService.persist_bom_risk(
                session,
                bom_id=bom_id,
                assessment=assessment,
            )
        )

        await session.commit()

        risk_id = record.id

    async with AsyncSessionLocal() as session:
        result = await session.get(
            BOMRiskRecord,
            risk_id,
        )

        assert result is not None
        assert result.bom_id == bom_id
        assert result.overall_score == 72.5
        assert result.severity == "HIGH"
        assert result.component_count == 25
        assert result.high_risk_count == 5
        assert result.critical_count == 2
        assert result.lifecycle_risk_count == 3
        assert result.availability_risk_count == 4

        assert result.details is not None

        details = json.loads(result.details)

        assert (
            details["top_risk_components"][0]["mpn"]
            == "LM358"
        )

        assert (
            details["top_risk_components"][0]["score"]
            == 92.5
        )

        assert (
            details["top_risk_components"][0]["lifecycle_risk"]
            is True
        )

        assert (
            details["top_risk_components"][0]["availability_risk"]
            is True
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


@pytest.mark.asyncio
async def test_persist_bom_risk_does_not_commit():
    suffix = uuid.uuid4().hex[:8]

    assessment = BOMRiskAssessment(
        overall_score=20.0,
        severity=RiskSeverity.MEDIUM,
        component_count=5,
        high_risk_count=1,
        critical_count=0,
        lifecycle_risk_count=1,
        availability_risk_count=0,
        top_risk_components=[],
    )

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"NO-COMMIT-BOM-{suffix}",
        )

        await session.commit()

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        await BOMRiskPersistenceService.persist_bom_risk(
            session,
            bom_id=bom_id,
            assessment=assessment,
        )

        # Roll back deliberately. The persistence service must
        # not commit the transaction itself.
        await session.rollback()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BOMRiskRecord).where(
                BOMRiskRecord.bom_id == bom_id
            )
        )

        assert result.scalar_one_or_none() is None

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id
            )
        )

        await session.commit()