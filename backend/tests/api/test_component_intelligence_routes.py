import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.app.db.repositories import ComponentRepository
from backend.app.db.repositories.lifecycle_repository import (   # <-- NEW IMPORT
    LifecycleRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.component import Component
from backend.app.intelligence.availability.models import (
    AvailabilityStatus,
    AvailabilitySummary,
    DistributorAvailability,
    ProcurementStatus,
)
from backend.app.intelligence.availability.procurement import (
    ComponentProcurementResult,
)
from backend.app.intelligence.component.models import (
    ComponentIntelligenceResult,
)
from backend.app.intelligence.decision.models import (
    ComponentDecision,
    DecisionAction,
    DecisionFactor,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
    LifecycleRisk,
    LifecycleStatus,
)
from backend.app.intelligence.risk.models import (
    ComponentRiskAssessment,
    RiskSeverity,
)


BASE_URL = "http://test"


class FakeIntelligenceService:
    """Deterministic intelligence service for API tests."""

    async def analyze(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int = 1,
    ) -> ComponentIntelligenceResult:

        distributor = ComponentEnrichmentResult(
            mpn=mpn,
            manufacturer=manufacturer,
            description="Test component",
            category="Test Category",
            package="SOIC-8",
            datasheet_url=None,
            manufacturer_part_url=None,
            availability=1000,
            lifecycle_status="ACTIVE",
            source="test",
        )

        availability = AvailabilitySummary(
            distributors=[
                DistributorAvailability(
                    distributor="test",
                    quantity_available=1000,
                    status=AvailabilityStatus.IN_STOCK,
                )
            ],
            total_distributor_quantity=1000,
            distributors_available=1,
            distributors_unavailable=0,
            best_available_quantity=1000,
            procurement_status=ProcurementStatus.READY,
        )

        procurement = ComponentProcurementResult(
            mpn=mpn,
            manufacturer=manufacturer,
            distributor_results=[distributor],
            availability=availability,
        )

        lifecycle = LifecycleAssessment(
            status=LifecycleStatus.ACTIVE,
            eol_date=None,
            last_buy_date=None,
            risk=LifecycleRisk.LOW,
            source="test",
        )

        risk = ComponentRiskAssessment(
            score=10.0,
            severity=RiskSeverity.LOW,
            lifecycle_score=0.0,
            availability_score=25.0,
            reasons=["Component is currently available."],
        )

        decision = ComponentDecision(
            mpn=mpn,
            manufacturer=manufacturer,
            action=DecisionAction.BUY,
            supplier="test",
            supplier_score=90.0,
            risk_score=10.0,
            lifecycle_status="ACTIVE",
            availability=1000,
            estimated_unit_price=1.5,
            estimated_total_cost=1.5 * quantity,
            currency="USD",
            factors=[
                DecisionFactor(
                    name="availability",
                    value="1000",
                    impact="positive",
                )
            ],
            reason="Component is suitable for procurement.",
        )

        return ComponentIntelligenceResult(
            mpn=mpn,
            manufacturer=manufacturer,
            procurement=procurement,
            lifecycle=lifecycle,
            risk=risk,
            decision=decision,
        )


@pytest.mark.asyncio
async def test_component_intelligence_returns_404_for_unknown_component():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/components/999999999/intelligence"
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Component 999999999 not found."
    )


@pytest.mark.asyncio
async def test_component_intelligence_returns_intelligence():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        component = Component(
            mpn=f"API-INTEL-{suffix}",
            manufacturer="Test Manufacturer",
        )

        session.add(component)
        await session.commit()

        component_id = component.id

    try:
        from backend.app.api.intelligence_routes import (
            get_intelligence_service,
        )

        app.dependency_overrides[
            get_intelligence_service
        ] = FakeIntelligenceService

        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                f"/api/v1/components/{component_id}/intelligence",
                params={"quantity": 10},
            )

        assert response.status_code == 200

        data = response.json()

        assert data["mpn"] == f"API-INTEL-{suffix}"
        assert (
            data["manufacturer"]
            == "Test Manufacturer"
        )

        assert (
            data["procurement"]["mpn"]
            == f"API-INTEL-{suffix}"
        )

        assert (
            data["procurement"]["availability"][
                "total_distributor_quantity"
            ]
            == 1000
        )

        assert (
            data["procurement"]["availability"][
                "procurement_status"
            ]
            == "READY"
        )

        assert (
            data["lifecycle"]["status"]
            == "ACTIVE"
        )

        # ---- Added lifecycle persistence verification ----
        async with AsyncSessionLocal() as session:
            lifecycle_records = (
                await LifecycleRepository.list_for_component(
                    session,
                    component_id,
                )
            )

            assert len(lifecycle_records) == 1

            lifecycle_record = lifecycle_records[0]

            assert lifecycle_record.component_id == component_id
            assert lifecycle_record.status == "ACTIVE"
            assert lifecycle_record.eol_date is None
            assert lifecycle_record.last_buy_date is None

        assert data["risk"]["score"] == 10.0
        assert data["risk"]["severity"] == "LOW"

        assert (
            data["decision"]["action"]
            == "BUY"
        )

        assert (
            data["decision"]["estimated_total_cost"]
            == 15.0
        )

    finally:
        app.dependency_overrides.clear()

        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(Component).where(
                    Component.id == component_id
                )
            )
            await session.commit()