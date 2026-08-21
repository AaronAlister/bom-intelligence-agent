from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories import RiskRepository
from backend.app.intelligence.risk.models import (
    ComponentRiskAssessment,
)
from backend.app.models.risk import RiskRecord


class RiskPersistenceService:

    @staticmethod
    async def persist_component_risk(
        session: AsyncSession,
        *,
        component_id: int,
        assessment: ComponentRiskAssessment,
    ) -> RiskRecord:
        """
        Persist a component risk assessment.

        The service does not commit the transaction.
        """

        details = {
            "lifecycle_score": (
                assessment.lifecycle_score
            ),
            "availability_score": (
                assessment.availability_score
            ),
            "reasons": assessment.reasons,
        }

        record = await RiskRepository.create(
            session,
            component_id=component_id,
            risk_type="COMPONENT",
            score=assessment.score,
            severity=assessment.severity.value,
            details=details,
        )

        return record