from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories import BOMRiskRepository
from backend.app.intelligence.risk.bom_explanation_models import (
    BOMRiskExplanation,
)
from backend.app.intelligence.risk.bom_models import (
    BOMRiskAssessment,
)
from backend.app.models.bom_risk import BOMRiskRecord


class BOMRiskPersistenceService:

    @staticmethod
    async def persist_bom_risk(
        session: AsyncSession,
        *,
        bom_id: int,
        assessment: BOMRiskAssessment,
        explanation: BOMRiskExplanation | None = None,
    ) -> BOMRiskRecord:
        """
        Persist a BOM risk assessment and optional explanation.

        The service does not commit the transaction.
        """

        details: dict[str, Any] = {
            "top_risk_components": [
                {
                    "component_id": component.component_id,
                    "mpn": component.mpn,
                    "quantity": component.quantity,
                    "score": component.score,
                    "severity": component.severity.value,
                    "lifecycle_risk": component.lifecycle_risk,
                    "availability_risk": component.availability_risk,
                }
                for component
                in assessment.top_risk_components
            ],
        }

        if explanation is not None:
            details["risk_drivers"] = [
                {
                    "component_id": driver.component_id,
                    "mpn": driver.mpn,
                    "score": driver.score,
                    "severity": driver.severity.value,
                    "reason": driver.reason,
                }
                for driver in explanation.risk_drivers
            ]

            details["recommendations"] = [
                {
                    "priority": recommendation.priority.value,
                    "component_id": recommendation.component_id,
                    "mpn": recommendation.mpn,
                    "action": recommendation.action,
                    "reason": recommendation.reason,
                }
                for recommendation
                in explanation.recommendations
            ]

            details["summary"] = explanation.summary

        record = await BOMRiskRepository.create(
            session,
            bom_id=bom_id,
            overall_score=assessment.overall_score,
            severity=assessment.severity.value,
            component_count=assessment.component_count,
            high_risk_count=assessment.high_risk_count,
            critical_count=assessment.critical_count,
            lifecycle_risk_count=(
                assessment.lifecycle_risk_count
            ),
            availability_risk_count=(
                assessment.availability_risk_count
            ),
            details=details,
        )

        return record