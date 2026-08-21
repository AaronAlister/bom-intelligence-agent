import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    BOMRepository,
    ComponentRepository,
    RiskRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component
from backend.app.services.bom_risk import (
    BOMRiskService,
)


@pytest.mark.asyncio
async def test_bom_risk_service_aggregates_component_risks():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"BOM-RISK-{suffix}",
            product="BOM Risk Test",
            revision="1.0",
        )

        component_a = await ComponentRepository.create(
            session,
            mpn=f"BOM-RISK-A-{suffix}",
            manufacturer="Test Manufacturer",
        )

        component_b = await ComponentRepository.create(
            session,
            mpn=f"BOM-RISK-B-{suffix}",
            manufacturer="Test Manufacturer",
        )

        component_c = await ComponentRepository.create(
            session,
            mpn=f"BOM-RISK-C-{suffix}",
            manufacturer="Test Manufacturer",
        )

        await session.flush()

        session.add_all(
            [
                BOMComponent(
                    bom_id=bom.id,
                    component_id=component_a.id,
                    quantity=10,
                ),
                BOMComponent(
                    bom_id=bom.id,
                    component_id=component_b.id,
                    quantity=2,
                ),
                BOMComponent(
                    bom_id=bom.id,
                    component_id=component_c.id,
                    quantity=1,
                ),
            ]
        )

        await session.flush()

        await RiskRepository.create(
            session,
            component_id=component_a.id,
            risk_type="COMPONENT",
            score=10.0,
            severity="LOW",
            details={
                "lifecycle_score": 0,
                "availability_score": 25,
            },
        )

        await RiskRepository.create(
            session,
            component_id=component_b.id,
            risk_type="COMPONENT",
            score=70.0,
            severity="HIGH",
            details={
                "lifecycle_score": 80,
                "availability_score": 50,
            },
        )

        await RiskRepository.create(
            session,
            component_id=component_c.id,
            risk_type="COMPONENT",
            score=95.0,
            severity="CRITICAL",
            details={
                "lifecycle_score": 100,
                "availability_score": 80,
            },
        )

        await session.commit()

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        result = await BOMRiskService.assess_bom(
            session,
            bom_id,
        )

        assert result.component_count == 3
        assert result.overall_score == 58.33

        assert (
            result.severity
            == RiskSeverity.HIGH
        )

        assert result.high_risk_count == 2
        assert result.critical_count == 1

        assert len(result.top_risk_components) == 3

        assert (
            result.top_risk_components[0].mpn
            == f"BOM-RISK-C-{suffix}"
        )

        assert (
            result.top_risk_components[1].mpn
            == f"BOM-RISK-B-{suffix}"
        )

        assert (
            result.top_risk_components[2].mpn
            == f"BOM-RISK-A-{suffix}"
        )

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id
            )
        )

        await session.commit()

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id.in_(
                    [
                        component_a.id,
                        component_b.id,
                        component_c.id,
                    ]
                )
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_bom_risk_service_uses_latest_risk_record():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"BOM-LATEST-{suffix}",
        )

        component = await ComponentRepository.create(
            session,
            mpn=f"BOM-LATEST-COMP-{suffix}",
        )

        await session.flush()

        session.add(
            BOMComponent(
                bom_id=bom.id,
                component_id=component.id,
                quantity=1,
            )
        )

        await session.flush()

        await RiskRepository.create(
            session,
            component_id=component.id,
            risk_type="COMPONENT",
            score=90.0,
            severity="CRITICAL",
        )

        await RiskRepository.create(
            session,
            component_id=component.id,
            risk_type="COMPONENT",
            score=10.0,
            severity="LOW",
        )

        await session.commit()

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        result = await BOMRiskService.assess_bom(
            session,
            bom_id,
        )

        assert result.component_count == 1
        assert result.overall_score == 10.0
        assert result.severity == RiskSeverity.LOW

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id
            )
        )

        await session.commit()

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component.id
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_bom_without_risk_records_is_unknown():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"BOM-NO-RISK-{suffix}",
        )

        component = await ComponentRepository.create(
            session,
            mpn=f"BOM-NO-RISK-COMP-{suffix}",
        )

        await session.flush()

        session.add(
            BOMComponent(
                bom_id=bom.id,
                component_id=component.id,
                quantity=1,
            )
        )

        await session.commit()

        bom_id = bom.id

    async with AsyncSessionLocal() as session:
        result = await BOMRiskService.assess_bom(
            session,
            bom_id,
        )

        assert result.component_count == 0
        assert result.overall_score == 0.0
        assert result.severity == RiskSeverity.UNKNOWN

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id
            )
        )

        await session.commit()

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component.id
            )
        )

        await session.commit()