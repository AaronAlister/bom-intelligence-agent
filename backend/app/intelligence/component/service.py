from backend.app.intelligence.availability.procurement_service import (
    ComponentProcurementService,
)
from backend.app.intelligence.availability.supplier.base import (
    SupplierQuoteProvider,
)
from backend.app.intelligence.availability.supplier.service import (
    SupplierQuoteService,
)
from backend.app.intelligence.component.models import (
    ComponentIntelligenceResult,
)
from backend.app.intelligence.decision.engine import (
    ComponentDecisionEngine,
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


class ComponentIntelligenceService:
    """
    Coordinates complete intelligence for a single component.

    Pipeline:

        Distributor enrichment
            ↓
        Procurement availability
            ↓
        Lifecycle assessment
            ↓
        Risk assessment
            ↓
        Supplier quotes
            ↓
        Procurement decision
    """

    def __init__(
        self,
        providers: list[ComponentEnrichmentProvider],
        quote_providers: list[SupplierQuoteProvider],
    ) -> None:
        self._procurement_service = (
            ComponentProcurementService(
                providers
            )
        )

        self._quote_service = SupplierQuoteService(
            quote_providers
        )

    async def analyze(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int = 1,
    ) -> ComponentIntelligenceResult:
        """
        Produce complete intelligence and a procurement
        decision for a component.
        """

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero"
            )

        procurement = (
            await self._procurement_service.analyze(
                mpn=mpn,
                manufacturer=manufacturer,
            )
        )

        lifecycle = LifecycleAssessor.assess(
            procurement.distributor_results
        )

        intelligence = ComponentIntelligenceResult(
            mpn=mpn,
            manufacturer=manufacturer,
            procurement=procurement,
            lifecycle=lifecycle,
        )

        risk = ComponentRiskAssessor.assess(
            intelligence
        )

        quotes = await self._quote_service.quote_all(
            mpn=mpn,
            manufacturer=manufacturer,
            quantity=quantity,
        )

        decision = ComponentDecisionEngine(
            quantity=quantity
        ).decide(
            mpn=mpn,
            manufacturer=manufacturer,
            quotes=quotes,
            risk=risk,
            lifecycle=lifecycle,
        )

        return ComponentIntelligenceResult(
            mpn=mpn,
            manufacturer=manufacturer,
            procurement=procurement,
            lifecycle=lifecycle,
            risk=risk,
            decision=decision,
        )

    @property
    def providers(
        self,
    ) -> tuple[ComponentEnrichmentProvider, ...]:
        """Return configured distributor providers."""

        return self._procurement_service.providers

    @property
    def quote_providers(
        self,
    ) -> tuple[SupplierQuoteProvider, ...]:
        """Return configured supplier quote providers."""

        return self._quote_service.providers