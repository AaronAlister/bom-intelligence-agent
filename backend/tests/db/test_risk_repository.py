import json
import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    ComponentRepository,
    RiskRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.component import Component


@pytest.mark.asyncio
async def test_risk_repository_create_and_get():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"RISK-REPO-{suffix}",
            manufacturer="Test Manufacturer",
        )

        await session.commit()

        component_id = component.id

    details = {
        "lifecycle_score": 80,
        "availability_score": 50,
        "reasons": [
            "Component is EOL.",
            "Only one distributor has stock.",
        ],
    }

    async with AsyncSessionLocal() as session:
        risk = await RiskRepository.create(
            session,
            component_id=component_id,
            risk_type="COMPONENT",
            score=68.0,
            severity="HIGH",
            details=details,
        )

        await session.commit()

        risk_id = risk.id

    async with AsyncSessionLocal() as session:
        fetched = await RiskRepository.get_by_id(
            session,
            risk_id,
        )

        assert fetched is not None
        assert fetched.component_id == component_id
        assert fetched.risk_type == "COMPONENT"
        assert fetched.score == 68.0
        assert fetched.severity == "HIGH"

        assert fetched.details is not None

        stored_details = json.loads(
            fetched.details
        )

        assert stored_details == details

        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_risk_repository_lists_component_risks():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"RISK-LIST-{suffix}",
            manufacturer="Test Manufacturer",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        first = await RiskRepository.create(
            session,
            component_id=component_id,
            risk_type="LIFECYCLE",
            score=80.0,
            severity="HIGH",
            details={
                "reason": "EOL component",
            },
        )

        second = await RiskRepository.create(
            session,
            component_id=component_id,
            risk_type="AVAILABILITY",
            score=50.0,
            severity="HIGH",
            details={
                "reason": "Single distributor",
            },
        )

        await session.commit()

        first_id = first.id
        second_id = second.id

    async with AsyncSessionLocal() as session:
        records = await RiskRepository.list_for_component(
            session,
            component_id,
        )

        assert len(records) == 2

        assert records[0].id == first_id
        assert records[1].id == second_id

        assert records[0].risk_type == "LIFECYCLE"
        assert records[1].risk_type == "AVAILABILITY"

        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_risk_repository_supports_null_details():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"RISK-NULL-{suffix}",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        risk = await RiskRepository.create(
            session,
            component_id=component_id,
            risk_type="COMPONENT",
            score=0.0,
            severity="LOW",
            details=None,
        )

        await session.commit()

        risk_id = risk.id

    async with AsyncSessionLocal() as session:
        fetched = await RiskRepository.get_by_id(
            session,
            risk_id,
        )

        assert fetched is not None
        assert fetched.details is None

        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()