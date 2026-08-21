from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories import (
    AlternativeRepository,
    ComponentRepository,
)
from backend.app.intelligence.alternatives.models import (
    AlternativeAnalysis,
)
from backend.app.models.alternative import AlternativeRecord


class AlternativePersistenceService:
    """
    Persists ranked alternative-component recommendations.

    The service does not commit the transaction.
    """

    @staticmethod
    async def persist_analysis(
        session: AsyncSession,
        *,
        source_component_id: int,
        analysis: AlternativeAnalysis,
    ) -> list[AlternativeRecord]:
        """
        Persist all alternative candidates from an analysis.

        Candidates that cannot be resolved to an existing
        component are skipped.
        """

        records: list[AlternativeRecord] = []

        for candidate in analysis.candidates:
            candidate_mpn = candidate.component.mpn

            if not candidate_mpn:
                continue

            alternative_component = (
                await ComponentRepository.get_by_mpn(
                    session,
                    candidate_mpn,
                )
            )

            if alternative_component is None:
                continue

            record = await AlternativeRepository.create(
                session,
                source_component_id=source_component_id,
                alternative_component_id=alternative_component.id,
                compatibility_score=(
                    candidate.compatibility_score
                ),
                category_match=candidate.category_match,
                package_match=candidate.package_match,
                manufacturer_match=(
                    candidate.manufacturer_match
                ),
                lifecycle_score=(
                    candidate.lifecycle_score
                ),
                availability_score=(
                    candidate.availability_score
                ),
                reasons=candidate.reasons,
            )

            records.append(record)

        return records