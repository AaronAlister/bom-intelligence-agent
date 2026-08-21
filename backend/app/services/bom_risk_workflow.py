from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.risk.bom_explanation_models import (
    BOMRiskExplanation,
)
from backend.app.intelligence.risk.bom_explainer import (
    BOMRiskExplainer,
)
from backend.app.intelligence.risk.bom_models import (
    BOMRiskAssessment,
)
from backend.app.models.bom_risk import BOMRiskRecord
from backend.app.services.bom_risk import BOMRiskService
from backend.app.services.bom_risk_persistence import (
    BOMRiskPersistenceService,
)


class BOMRiskWorkflowService:
    """
    End-to-end BOM risk workflow.

    Coordinates BOM risk assessment, explanation,
    recommendations, and persistence.

    Component-level risk records must already exist
    before this workflow is executed.

    The service does not commit the transaction.
    """

    @staticmethod
    async def analyze_and_persist(
        session: AsyncSession,
        bom_id: int,
    ) -> tuple[
        BOMRiskAssessment,
        BOMRiskExplanation,
        BOMRiskRecord,
    ]:
        """
        Assess a BOM using persisted component risk records,
        generate explanations and recommendations, and
        persist the resulting BOM risk snapshot.
        """

        assessment = await BOMRiskService.assess_bom(
            session,
            bom_id,
        )

        explanation = BOMRiskExplainer.explain(
            assessment
        )

        risk_record = (
            await BOMRiskPersistenceService.persist_bom_risk(
                session,
                bom_id=bom_id,
                assessment=assessment,
                explanation=explanation,
            )
        )

        return (
            assessment,
            explanation,
            risk_record,
        )