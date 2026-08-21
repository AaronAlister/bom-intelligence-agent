from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.risk.bom_assessor import (
    BOMRiskAssessor,
)
from backend.app.intelligence.risk.bom_models import (
    BOMComponentRisk,
    BOMRiskAssessment,
)
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)
from backend.app.models.bom_component import BOMComponent
from backend.app.models.risk import RiskRecord


class BOMRiskService:
    """
    Builds a BOM-level risk assessment from persisted
    component risk records.

    The service does not commit the transaction.
    """

    @staticmethod
    async def assess_bom(
        session: AsyncSession,
        bom_id: int,
    ) -> BOMRiskAssessment:
        """
        Assess the risk profile of a BOM.

        Components without a persisted risk record are
        ignored because there is not enough information to
        classify their component-level risk.
        """

        result = await session.execute(
            select(BOMComponent, RiskRecord)
            .options(
                selectinload(BOMComponent.component)
            )
            .join(
                RiskRecord,
                RiskRecord.component_id
                == BOMComponent.component_id,
            )
            .where(
                BOMComponent.bom_id == bom_id
            )
            .order_by(
                BOMComponent.id,
                RiskRecord.id.desc(),
            )
        )

        rows = result.all()

        component_risks: list[BOMComponentRisk] = []

        seen_components: set[int] = set()

        for bom_component, risk_record in rows:
            component_id = bom_component.component_id

            # A component can have multiple historical risk
            # records. Use the most recent one only.
            if component_id in seen_components:
                continue

            seen_components.add(component_id)

            try:
                severity = RiskSeverity(
                    risk_record.severity
                )
            except ValueError:
                severity = RiskSeverity.UNKNOWN

            component_risks.append(
                BOMComponentRisk(
                    component_id=component_id,
                    mpn=bom_component.component.mpn,
                    quantity=bom_component.quantity,
                    score=risk_record.score,
                    severity=severity,
                    lifecycle_risk=(
                        risk_record.risk_type
                        in {
                            "LIFECYCLE",
                            "COMPONENT",
                        }
                        and risk_record.severity
                        in {
                            "HIGH",
                            "CRITICAL",
                        }
                    ),
                    availability_risk=(
                        risk_record.risk_type
                        in {
                            "AVAILABILITY",
                            "COMPONENT",
                        }
                        and risk_record.severity
                        in {
                            "HIGH",
                            "CRITICAL",
                        }
                    ),
                )
            )

        return BOMRiskAssessor.assess(
            component_risks
        )