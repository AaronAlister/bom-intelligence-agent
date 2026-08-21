from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.alternatives.models import (
    AlternativeAnalysis,
)
from backend.app.intelligence.component.service import (
    ComponentIntelligenceService,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.services.alternative_component import (
    AlternativeComponentService,
)
from backend.app.services.alternative_persistence import (
    AlternativePersistenceService,
)


class AlternativeWorkflowService:
    """
    End-to-end alternative analysis workflow.

    Performs alternative discovery/ranking and explicitly
    persists the resulting recommendation history.

    The service does not commit the transaction.
    """

    @staticmethod
    async def analyze_and_persist(
        session: AsyncSession,
        *,
        component_id: int,
        source_enrichment: ComponentEnrichmentResult,
        limit: int = 10,
        intelligence_service: (
            ComponentIntelligenceService | None
        ) = None,
    ) -> tuple[
        AlternativeAnalysis,
        int,
    ]:
        """
        Analyze alternatives and persist the resulting
        candidates.

        Returns:
            The ranked analysis and the number of records
            persisted.
        """

        analysis = (
            await AlternativeComponentService
            .find_alternatives(
                session,
                component_id=component_id,
                source_enrichment=source_enrichment,
                limit=limit,
                intelligence_service=intelligence_service,
            )
        )

        records = (
            await AlternativePersistenceService
            .persist_analysis(
                session,
                source_component_id=component_id,
                analysis=analysis,
            )
        )

        return analysis, len(records)