from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories import ComponentRepository
from backend.app.intelligence.alternatives.matcher import (
    AlternativeMatcher,
)
from backend.app.intelligence.alternatives.models import (
    AlternativeAnalysis,
)
from backend.app.intelligence.availability.supplier.base import (
    SupplierQuoteProvider,
)
from backend.app.intelligence.component.service import (
    ComponentIntelligenceService,
)
from backend.app.intelligence.enrichment.factory import (
    create_default_registry,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


def create_component_intelligence_service() -> (
    ComponentIntelligenceService
):
    """
    Create the component intelligence service using
    the configured distributor and supplier providers.
    """

    registry = create_default_registry()

    distributors = [
        registry.get("mouser"),
        registry.get("arrow"),
        registry.get("digikey"),
    ]

    quote_providers = cast(
        list[SupplierQuoteProvider],
        [
            registry.get("mouser"),
            registry.get("arrow"),
            registry.get("digikey"),
        ],
    )

    return ComponentIntelligenceService(
        distributors,
        quote_providers,
    )


class AlternativeComponentService:
    """
    Discovers and ranks alternatives for a persisted component.

    Candidate discovery is performed against the local component
    catalog. External intelligence is optional and must not prevent
    the alternative analysis from completing when providers are
    unavailable.

    The service does not commit the transaction.
    """

    @staticmethod
    async def find_alternatives(
        session: AsyncSession,
        *,
        component_id: int,
        source_enrichment: ComponentEnrichmentResult,
        limit: int = 10,
        intelligence_service: (
            ComponentIntelligenceService | None
        ) = None,
    ) -> AlternativeAnalysis:
        """
        Find compatible alternatives for a persisted component.
        """

        if limit < 1:
            raise ValueError(
                "Alternative limit must be at least 1."
            )

        component = await ComponentRepository.get_by_id(
            session,
            component_id,
        )

        if component is None:
            raise ValueError(
                f"Component {component_id} not found."
            )

        # Discover candidates using broad filters (same category, package, or manufacturer)
        candidates = (
            await ComponentRepository
            .list_alternative_candidates(
                session,
                category=component.category,
                package=component.package,
                manufacturer=component.manufacturer,
                exclude_component_id=component.id,
            )
        )

        if not candidates:
            return AlternativeMatcher.analyze(
                source=source_enrichment,
                candidates=[],
            )

        candidate_enrichment: list[
            ComponentEnrichmentResult
        ] = []

        for candidate in candidates:
            fallback_result = (
                AlternativeComponentService
                ._to_enrichment_result(candidate)
            )

            # ----------------------------------------------------------
            # Gate: reject candidates using the central compatibility logic.
            # Do not duplicate the matcher's internal rules.
            # ----------------------------------------------------------
            if not AlternativeMatcher.is_compatible(
                source=source_enrichment,
                candidate=fallback_result,
            ):
                continue

            # Attempt external intelligence if service provided
            candidate_result = fallback_result

            if intelligence_service is not None:
                candidate_result = (
                    await AlternativeComponentService
                    ._try_enrich_candidate(
                        candidate=candidate,
                        intelligence_service=(
                            intelligence_service
                        ),
                        fallback=fallback_result,
                    )
                )

            candidate_enrichment.append(
                candidate_result
            )

        # Run the authoritative matcher
        analysis = AlternativeMatcher.analyze(
            source=source_enrichment,
            candidates=candidate_enrichment,
        )

        # Apply limit
        analysis.candidates = (
            analysis.candidates[:limit]
        )

        analysis.best_candidate = (
            analysis.candidates[0]
            if analysis.candidates
            else None
        )

        return analysis

    @staticmethod
    async def _try_enrich_candidate(
        *,
        candidate,
        intelligence_service: ComponentIntelligenceService,
        fallback: ComponentEnrichmentResult,
    ) -> ComponentEnrichmentResult:
        """
        Attempt external intelligence enrichment.

        Any provider failure falls back immediately to the
        locally persisted component data.
        """

        try:
            intelligence = (
                await intelligence_service.analyze(
                    mpn=candidate.mpn,
                    manufacturer=candidate.manufacturer,
                )
            )

        except Exception:
            return fallback

        lifecycle_status = (
            intelligence.lifecycle.status.value
            if intelligence.lifecycle.status is not None
            else None
        )

        availability = (
            intelligence.procurement.availability
            .best_available_quantity
        )

        return ComponentEnrichmentResult(
            mpn=candidate.mpn,
            manufacturer=candidate.manufacturer,
            description=candidate.description,
            category=candidate.category,
            package=candidate.package,
            lifecycle_status=lifecycle_status,
            availability=availability,
            source="component_intelligence",
        )

    @staticmethod
    def _to_enrichment_result(
        component,
    ) -> ComponentEnrichmentResult:
        """
        Convert persisted component data into the enrichment
        model used by AlternativeMatcher.
        """

        return ComponentEnrichmentResult(
            mpn=component.mpn,
            manufacturer=component.manufacturer,
            description=component.description,
            category=component.category,
            package=component.package,
            lifecycle_status=None,
            availability=None,
            source="component_catalog",
        )