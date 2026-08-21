from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories import LifecycleRepository
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
)
from backend.app.models.lifecycle import LifecycleRecord


class LifecyclePersistenceService:
    """Persist lifecycle assessments for components."""

    @staticmethod
    async def persist_component_lifecycle(
        session: AsyncSession,
        *,
        component_id: int,
        assessment: LifecycleAssessment,
    ) -> LifecycleRecord:
        """
        Persist a component lifecycle assessment.

        The service does not commit the transaction.
        """

        return await LifecycleRepository.create(
            session,
            component_id=component_id,
            status=assessment.status.value,
            eol_date=assessment.eol_date,
            last_buy_date=assessment.last_buy_date,
        )