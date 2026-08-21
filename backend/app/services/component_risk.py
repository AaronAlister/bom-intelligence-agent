from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.availability.procurement_service import (
    ComponentProcurementService,
)
from backend.app.intelligence.component.models import (
    ComponentIntelligenceResult,
)
from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.lifecycle.assessor import (
    LifecycleAssessor,
)
from backend.app.intelligence.risk.assessor import (
    ComponentRiskAssessor,
)
from backend.app.models.component import Component
from backend.app.models.lifecycle import LifecycleRecord
from backend.app.models.risk import RiskRecord
from backend.app.services.lifecycle_persistence import (
    LifecyclePersistenceService,
)
from backend.app.services.risk_persistence import (
    RiskPersistenceService,
)


class ComponentRiskService:
    """
    End-to-end component intelligence workflow.

    Coordinates component procurement intelligence,
    lifecycle assessment, risk assessment, and persistence.

    The service does not commit the transaction.
    """

    @staticmethod
    async def analyze_and_persist(
        session: AsyncSession,
        component: Component,
        providers: list[ComponentEnrichmentProvider],
    ) -> tuple[
        ComponentIntelligenceResult,
        LifecycleRecord,
        RiskRecord,
    ]:
        """
        Analyze a component and persist its lifecycle and risk.

        Returns:
            A tuple containing:
            - the complete intelligence result
            - the persisted lifecycle record
            - the persisted risk record
        """

        procurement_service = (
            ComponentProcurementService(providers)
        )

        procurement = await procurement_service.analyze(
            mpn=component.mpn,
            manufacturer=component.manufacturer,
        )

        lifecycle = LifecycleAssessor.assess(
            procurement.distributor_results
        )

        intelligence = ComponentIntelligenceResult(
            mpn=component.mpn,
            manufacturer=component.manufacturer,
            procurement=procurement,
            lifecycle=lifecycle,
        )

        lifecycle_record = (
            await LifecyclePersistenceService
            .persist_component_lifecycle(
                session,
                component_id=component.id,
                assessment=lifecycle,
            )
        )

        assessment = ComponentRiskAssessor.assess(
            intelligence
        )

        intelligence.risk = assessment

        risk_record = (
            await RiskPersistenceService
            .persist_component_risk(
                session,
                component_id=component.id,
                assessment=assessment,
            )
        )

        return (
            intelligence,
            lifecycle_record,
            risk_record,
        )