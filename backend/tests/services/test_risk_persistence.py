import json
import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    ComponentRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.risk.models import (
    ComponentRiskAssessment,
    RiskSeverity,
)
from backend.app.models.component import Component
from backend.app.services.risk_persistence import (
    RiskPersistenceService,
)


@pytest.mark.asyncio
async def test_persist_component_risk():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"RISK-SERVICE-{suffix}",
            manufacturer="Test Manufacturer",
        )

        await session.commit()

        component_id = component.id

    assessment = ComponentRiskAssessment(
        score=92.0,
        severity=RiskSeverity.CRITICAL,
        lifecycle_score=100.0,
        availability_score=80.0,
        reasons=[
            "Component is obsolete or discontinued.",
            "No distributor currently reports available stock.",
        ],
    )

    async with AsyncSessionLocal() as session:
        record = (
            await RiskPersistenceService
            .persist_component_risk(
                session,
                component_id=component_id,
                assessment=assessment,
            )
        )

        await session.commit()

        assert record.component_id == component_id
        assert record.risk_type == "COMPONENT"
        assert record.score == 92.0
        assert record.severity == "CRITICAL"

        assert record.details is not None

        details = json.loads(
            record.details
        )

        assert details["lifecycle_score"] == 100.0
        assert details["availability_score"] == 80.0

        assert len(details["reasons"]) == 2

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()