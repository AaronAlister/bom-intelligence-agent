from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.factory import (
    create_default_registry,
)
from backend.app.models.bom_component import BOMComponent
from backend.app.services.component_risk import (
    ComponentRiskService,
)


class BOMComponentRiskService:
    """
    Runs component-level risk analysis for every component
    belonging to a BOM.

    This service is responsible only for generating and
    persisting component-level RiskRecord entries.

    BOM-level aggregation is handled separately by
    BOMRiskWorkflowService.

    The service does not commit the transaction.
    """

    @staticmethod
    async def analyze_bom_components(
        session: AsyncSession,
        bom_id: int,
    ) -> int:
        """
        Analyze every component belonging to a BOM.

        Returns:
            Number of components successfully analyzed.
        """

        result = await session.execute(
            select(BOMComponent)
            .options(
                selectinload(BOMComponent.component)
            )
            .where(
                BOMComponent.bom_id == bom_id
            )
            .order_by(
                BOMComponent.id
            )
        )

        bom_components = list(
            result.scalars().all()
        )

        registry = create_default_registry()

        providers: list[
            ComponentEnrichmentProvider
        ] = [
            registry.get("mouser"),
            registry.get("arrow"),
            registry.get("digikey"),
        ]

        analyzed_count = 0

        for bom_component in bom_components:
            await ComponentRiskService.analyze_and_persist(
                session=session,
                component=bom_component.component,
                providers=providers,
            )

            analyzed_count += 1

        return analyzed_count