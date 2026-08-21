from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ingestion.normalizer import (
    normalize_manufacturer,
    normalize_mpn,
    normalize_text,
)
from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.orchestrator import (
    EnrichmentOrchestrator,
)
from backend.app.models.component import Component


class ComponentEnrichmentService:
    """Services for initializing and maintaining component enrichment data."""

    @staticmethod
    async def backfill_normalized_identity(
        session: AsyncSession,
    ) -> int:
        """
        Populate normalized identity fields for components that
        predate Phase 5.

        Returns:
            Number of components updated.
        """

        result = await session.execute(
            select(Component).where(
                Component.normalized_mpn.is_(None)
            )
        )

        components = list(result.scalars().all())

        updated_count = 0

        for component in components:
            normalized_mpn = normalize_mpn(component.mpn)

            if normalized_mpn is None:
                continue

            component.normalized_mpn = normalized_mpn
            component.normalized_manufacturer = (
                normalize_manufacturer(component.manufacturer)
            )

            updated_count += 1

        await session.flush()

        return updated_count

    @staticmethod
    async def enrich_component(
        session: AsyncSession,
        component: Component,
    ) -> Component:
        """
        Enrich a component using deterministic local metadata.

        External distributor and datasheet enrichment will be added
        in later Phase 5 sub-phases.
        """

        normalized_mpn = normalize_mpn(component.mpn)

        if normalized_mpn is None:
            raise ValueError(
                "Component MPN is required for enrichment"
            )

        component.normalized_mpn = normalized_mpn

        component.normalized_manufacturer = normalize_manufacturer(
            component.manufacturer
        )

        component.normalized_category = normalize_text(
            component.category
        )

        component.enrichment_status = "ENRICHED"

        component.enriched_at = datetime.now(timezone.utc)

        await session.flush()

        return component

    @staticmethod
    async def enrich_with_provider(
        session: AsyncSession,
        component: Component,
        provider: ComponentEnrichmentProvider,
    ) -> Component:
        """
        Enrich a component using an external enrichment provider.

        The provider is responsible for retrieving component data.
        This service is responsible for applying that data to the
        Component model and maintaining enrichment state.

        The service does not commit the transaction.
        """

        normalized_mpn = normalize_mpn(component.mpn)

        if normalized_mpn is None:
            raise ValueError(
                "Component MPN is required for enrichment"
            )

        normalized_manufacturer = normalize_manufacturer(
            component.manufacturer
        )

        component.enrichment_status = "ENRICHING"

        await session.flush()

        try:
            result = await provider.enrich(
                mpn=normalized_mpn,
                manufacturer=normalized_manufacturer,
            )

        except Exception:
            component.enrichment_status = "FAILED"
            await session.flush()
            raise

        if result is None:
            component.enrichment_status = "NOT_FOUND"
            await session.flush()
            return component

        # Apply provider data only when the provider supplied it.
        if result.manufacturer is not None:
            component.manufacturer = normalize_manufacturer(
                result.manufacturer
            )

        if result.mpn is not None:
            normalized_result_mpn = normalize_mpn(
                result.mpn
            )

            if normalized_result_mpn is not None:
                component.mpn = normalized_result_mpn
                component.normalized_mpn = normalized_result_mpn

        if result.description is not None:
            component.description = normalize_text(
                result.description
            )

        if result.category is not None:
            component.category = normalize_text(
                result.category
            )
            component.normalized_category = normalize_text(
                result.category
            )

        if result.package is not None:
            component.package = normalize_text(
                result.package
            )

        if result.datasheet_url is not None:
            component.datasheet_url = result.datasheet_url

        if result.manufacturer_part_url is not None:
            component.manufacturer_part_url = (
                result.manufacturer_part_url
            )

        component.normalized_manufacturer = (
            normalize_manufacturer(component.manufacturer)
        )

        component.enrichment_status = "ENRICHED"
        component.enriched_at = datetime.now(timezone.utc)

        await session.flush()

        return component

    @staticmethod
    async def enrich_with_orchestrator(
        session: AsyncSession,
        component: Component,
        orchestrator: EnrichmentOrchestrator,
    ) -> Component:
        """
        Enrich a component through the provider orchestrator.

        The orchestrator handles provider priority and fallback.
        This service persists the resulting enrichment data and
        distinguishes genuine NOT_FOUND results from provider
        failures.

        The service does not commit the transaction.
        """

        normalized_mpn = normalize_mpn(component.mpn)

        if normalized_mpn is None:
            raise ValueError(
                "Component MPN is required for enrichment"
            )

        normalized_manufacturer = normalize_manufacturer(
            component.manufacturer
        )

        component.enrichment_status = "ENRICHING"

        await session.flush()

        try:
            outcome = await orchestrator.enrich(
                mpn=normalized_mpn,
                manufacturer=normalized_manufacturer,
            )

        except Exception:
            component.enrichment_status = "FAILED"
            await session.flush()
            raise

        result = outcome.result

        if result is None:
            if outcome.all_providers_failed:
                component.enrichment_status = "FAILED"
            else:
                component.enrichment_status = "NOT_FOUND"

            await session.flush()

            return component

        if result.manufacturer is not None:
            component.manufacturer = normalize_manufacturer(
                result.manufacturer
            )

        if result.mpn is not None:
            normalized_result_mpn = normalize_mpn(
                result.mpn
            )

            if normalized_result_mpn is not None:
                component.mpn = normalized_result_mpn
                component.normalized_mpn = normalized_result_mpn

        if result.description is not None:
            component.description = normalize_text(
                result.description
            )

        if result.category is not None:
            component.category = normalize_text(
                result.category
            )
            component.normalized_category = normalize_text(
                result.category
            )

        if result.package is not None:
            component.package = normalize_text(
                result.package
            )

        if result.datasheet_url is not None:
            component.datasheet_url = result.datasheet_url

        if result.manufacturer_part_url is not None:
            component.manufacturer_part_url = (
                result.manufacturer_part_url
            )

        component.normalized_manufacturer = (
            normalize_manufacturer(component.manufacturer)
        )

        component.enrichment_status = "ENRICHED"
        component.enriched_at = datetime.now(timezone.utc)

        await session.flush()

        return component