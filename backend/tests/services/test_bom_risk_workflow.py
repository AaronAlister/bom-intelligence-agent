import json
import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    BOMRepository,
    RiskRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.risk.models import RiskSeverity
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component
from backend.app.models.bom_risk import BOMRiskRecord
from backend.app.services.bom_risk_workflow import (
    BOMRiskWorkflowService,
)


@pytest.mark.asyncio
async def test_bom_risk_workflow_analyzes_and_persists():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"WORKFLOW-BOM-{suffix}",
            product="Workflow Test",
            revision="1.0",
        )

        component_a = Component(
            mpn=f"WORKFLOW-A-{suffix}",
            manufacturer="Texas Instruments",
        )

        component_b = Component(
            mpn=f"WORKFLOW-B-{suffix}",
            manufacturer="Texas Instruments",
        )

        component_c = Component(
            mpn=f"WORKFLOW-C-{suffix}",
            manufacturer="Texas Instruments",
        )

        session.add_all(
            [
                component_a,
                component_b,
                component_c,
            ]
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
                    quantity=5,
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
                "lifecycle_score": 0.0,
                "availability_score": 20.0,
                "reasons": [],
            },
        )

        await RiskRepository.create(
            session,
            component_id=component_b.id,
            risk_type="COMPONENT",
            score=70.0,
            severity="HIGH",
            details={
                "lifecycle_score": 80.0,
                "availability_score": 60.0,
                "reasons": [
                    "Lifecycle risk detected",
                ],
            },
        )

        await RiskRepository.create(
            session,
            component_id=component_c.id,
            risk_type="COMPONENT",
            score=95.0,
            severity="CRITICAL",
            details={
                "lifecycle_score": 100.0,
                "availability_score": 90.0,
                "reasons": [
                    "Critical lifecycle risk",
                    "Critical availability risk",
                ],
            },
        )

        await session.commit()

        bom_id = bom.id
        component_a_id = component_a.id
        component_b_id = component_b.id
        component_c_id = component_c.id

    async with AsyncSessionLocal() as session:
        assessment, explanation, record = (
            await BOMRiskWorkflowService.analyze_and_persist(
                session,
                bom_id,
            )
        )

        await session.commit()

        assert assessment.component_count == 3
        assert assessment.overall_score == 58.33
        assert assessment.severity == RiskSeverity.HIGH

        assert explanation.summary != ""
        assert len(explanation.risk_drivers) == 2
        assert len(explanation.recommendations) > 0

        assert assessment.high_risk_count == 2
        assert assessment.critical_count == 1

        assert record.bom_id == bom_id
        assert record.overall_score == 58.33
        assert record.severity == "HIGH"

        assert record.component_count == 3
        assert record.high_risk_count == 2
        assert record.critical_count == 1

        assert record.details is not None

        details = json.loads(record.details)

        assert len(
            details["top_risk_components"]
        ) == 3

        assert (
            details["top_risk_components"][0]["mpn"]
            == f"WORKFLOW-C-{suffix}"
        )

        assert (
            details["top_risk_components"][1]["mpn"]
            == f"WORKFLOW-B-{suffix}"
        )

        assert (
            details["top_risk_components"][2]["mpn"]
            == f"WORKFLOW-A-{suffix}"
        )

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

        await session.execute(
            delete(Component).where(
                Component.id.in_(
                    [
                        component_a_id,
                        component_b_id,
                        component_c_id,
                    ]
                )
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_bom_risk_workflow_handles_bom_without_risks():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"EMPTY-RISK-BOM-{suffix}",
        )

        component = Component(
            mpn=f"EMPTY-RISK-COMP-{suffix}",
            manufacturer="Test Manufacturer",
        )

        session.add(component)

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
        component_id = component.id

    async with AsyncSessionLocal() as session:
        assessment, explanation, record = (
            await BOMRiskWorkflowService.analyze_and_persist(
                session,
                bom_id,
            )
        )

        await session.commit()

        assert assessment.component_count == 0
        assert assessment.overall_score == 0.0
        assert assessment.severity == RiskSeverity.UNKNOWN

        assert explanation.summary != ""

        assert record.bom_id == bom_id
        assert record.overall_score == 0.0
        assert record.severity == "UNKNOWN"

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

        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()