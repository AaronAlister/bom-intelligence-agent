import uuid

import pytest

from backend.app.db.repositories import ComponentRepository
from backend.app.db.repositories.lifecycle_repository import (
    LifecycleRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
    LifecycleRisk,
    LifecycleStatus,
)
from backend.app.services.lifecycle_persistence import (
    LifecyclePersistenceService,
)


@pytest.mark.asyncio
async def test_persist_component_lifecycle() -> None:
    suffix = uuid.uuid4().hex[:8]
    mpn = f"LIFECYCLE-TEST-{suffix}"

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=mpn,
            manufacturer="STMicroelectronics",
            category="MCU",
            package="LQFP-100",
        )

        await session.commit()

        component_id = component.id

    assessment = LifecycleAssessment(
        status=LifecycleStatus.EOL,
        eol_date=None,
        last_buy_date=None,
        risk=LifecycleRisk.HIGH,
        source="test",
    )

    async with AsyncSessionLocal() as session:
        record = (
            await LifecyclePersistenceService
            .persist_component_lifecycle(
                session,
                component_id=component_id,
                assessment=assessment,
            )
        )

        await session.commit()

        assert record.id is not None
        assert record.component_id == component_id
        assert record.status == "EOL"
        assert record.eol_date is None
        assert record.last_buy_date is None

    async with AsyncSessionLocal() as session:
        records = (
            await LifecycleRepository
            .list_for_component(
                session,
                component_id,
            )
        )

        assert len(records) == 1
        assert records[0].status == "EOL"