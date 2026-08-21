import json
import uuid
from typing import cast

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import ComponentRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.models.component import Component
from backend.app.services.component_risk import ComponentRiskService


class MockProvider(ComponentEnrichmentProvider):
    def __init__(
        self,
        provider_name: str,
        result: ComponentEnrichmentResult | None,
    ) -> None:
        self._name = provider_name
        self._result = result
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        self.calls += 1
        return self._result


@pytest.mark.asyncio
async def test_component_risk_service_analyzes_and_persists():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"RISK-WORKFLOW-{suffix}",
            manufacturer="Texas Instruments",
        )

        await session.commit()

        component_id = component.id

    mock_providers: list[MockProvider] = [
        MockProvider(
            "mouser",
            ComponentEnrichmentResult(
                mpn=f"RISK-WORKFLOW-{suffix}",
                manufacturer="Texas Instruments",
                availability=5000,
                lifecycle_status="ACTIVE",
                source="mouser",
            ),
        ),
        MockProvider(
            "arrow",
            ComponentEnrichmentResult(
                mpn=f"RISK-WORKFLOW-{suffix}",
                manufacturer="Texas Instruments",
                availability=4200,
                lifecycle_status="ACTIVE",
                source="arrow",
            ),
        ),
        MockProvider(
            "digikey",
            ComponentEnrichmentResult(
                mpn=f"RISK-WORKFLOW-{suffix}",
                manufacturer="Texas Instruments",
                availability=8100,
                lifecycle_status="ACTIVE",
                source="digikey",
            ),
        ),
    ]

    async with AsyncSessionLocal() as session:
        intelligence, lifecycle_record, risk = (
            await ComponentRiskService.analyze_and_persist(
                session,
                component,
                cast(
                    list[ComponentEnrichmentProvider],
                    mock_providers,
                ),
            )
        )

        await session.commit()

        assert (
            intelligence.mpn
            == f"RISK-WORKFLOW-{suffix}"
        )

        assert (
            intelligence.procurement
            .availability
            .total_distributor_quantity
            == 17300
        )

        assert (
            intelligence.lifecycle.status.value
            == "ACTIVE"
        )

        assert risk.component_id == component_id
        assert risk.risk_type == "COMPONENT"
        assert risk.score == 0.0
        assert risk.severity == "LOW"

        assert risk.details is not None

        details = json.loads(risk.details)

        assert details["lifecycle_score"] == 0.0
        assert details["availability_score"] == 0.0
        assert len(details["reasons"]) == 2

        assert all(
            provider.calls == 1
            for provider in mock_providers
        )

        assert lifecycle_record.component_id == component_id
        assert lifecycle_record.status == "ACTIVE"
        assert lifecycle_record.eol_date is None
        assert lifecycle_record.last_buy_date is None

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_component_risk_service_persists_high_risk():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"RISK-HIGH-{suffix}",
            manufacturer="Legacy Manufacturer",
        )

        await session.commit()

        component_id = component.id

    mock_providers: list[MockProvider] = [
        MockProvider(
            "mouser",
            ComponentEnrichmentResult(
                mpn=f"RISK-HIGH-{suffix}",
                manufacturer="Legacy Manufacturer",
                availability=0,
                lifecycle_status="OBSOLETE",
                source="mouser",
            ),
        ),
        MockProvider(
            "arrow",
            ComponentEnrichmentResult(
                mpn=f"RISK-HIGH-{suffix}",
                manufacturer="Legacy Manufacturer",
                availability=0,
                lifecycle_status="OBSOLETE",
                source="arrow",
            ),
        ),
    ]

    async with AsyncSessionLocal() as session:
        intelligence, lifecycle_record, risk = (
            await ComponentRiskService.analyze_and_persist(
                session,
                component,
                cast(
                    list[ComponentEnrichmentProvider],
                    mock_providers,
                ),
            )
        )

        await session.commit()

        assert (
            intelligence.lifecycle.status.value
            == "OBSOLETE"
        )

        assert risk.component_id == component_id
        assert risk.score == 92.0
        assert risk.severity == "CRITICAL"

        assert lifecycle_record.component_id == component_id
        assert lifecycle_record.status == "OBSOLETE"
        assert lifecycle_record.eol_date is None
        assert lifecycle_record.last_buy_date is None

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_component_risk_service_persists_nrnd_lifecycle() -> None:
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"RISK-NRND-{suffix}",
            manufacturer="Test Manufacturer",
        )

        await session.commit()

        component_id = component.id

    mock_providers: list[MockProvider] = [
        MockProvider(
            "mouser",
            ComponentEnrichmentResult(
                mpn=f"RISK-NRND-{suffix}",
                manufacturer="Test Manufacturer",
                availability=5000,
                lifecycle_status="NRND",
                source="mouser",
            ),
        ),
    ]

    async with AsyncSessionLocal() as session:
        intelligence, lifecycle_record, risk = (
            await ComponentRiskService.analyze_and_persist(
                session,
                component,
                cast(
                    list[ComponentEnrichmentProvider],
                    mock_providers,
                ),
            )
        )

        await session.commit()

        assert intelligence.lifecycle.status.value == "NRND"
        assert intelligence.lifecycle.risk.value == "MEDIUM"

        assert lifecycle_record.component_id == component_id
        assert lifecycle_record.status == "NRND"

        assert risk.component_id == component_id

        # NRND lifecycle = 50
        # One available distributor = 50 availability risk
        # Final score = (50 * 0.60) + (50 * 0.40) = 50
        assert risk.score == 50.0
        assert risk.severity == "HIGH"

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_component_risk_service_persists_eol_lifecycle() -> None:
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"RISK-EOL-{suffix}",
            manufacturer="Test Manufacturer",
        )

        await session.commit()

        component_id = component.id

    mock_providers: list[MockProvider] = [
        MockProvider(
            "mouser",
            ComponentEnrichmentResult(
                mpn=f"RISK-EOL-{suffix}",
                manufacturer="Test Manufacturer",
                availability=5000,
                lifecycle_status="EOL",
                source="mouser",
            ),
        ),
    ]

    async with AsyncSessionLocal() as session:
        intelligence, lifecycle_record, risk = (
            await ComponentRiskService.analyze_and_persist(
                session,
                component,
                cast(
                    list[ComponentEnrichmentProvider],
                    mock_providers,
                ),
            )
        )

        await session.commit()

        assert intelligence.lifecycle.status.value == "EOL"
        assert intelligence.lifecycle.risk.value == "HIGH"

        assert lifecycle_record.component_id == component_id
        assert lifecycle_record.status == "EOL"

        assert risk.component_id == component_id
        assert risk.severity == "HIGH"

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )

        await session.commit()