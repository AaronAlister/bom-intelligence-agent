from backend.app.intelligence.risk.bom_explanation_models import (
    BOMRiskDriver,
    BOMRiskExplanation,
    BOMRiskRecommendation,
)
from backend.app.intelligence.risk.bom_models import (
    BOMRiskAssessment,
)
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)


class BOMRiskExplainer:
    """
    Converts a BOM risk assessment into explainable
    risk drivers and procurement recommendations.
    """

    @staticmethod
    def explain(
        assessment: BOMRiskAssessment,
    ) -> BOMRiskExplanation:
        """
        Generate an explanation and recommendations for
        a BOM risk assessment.
        """

        if assessment.component_count == 0:
            return BOMRiskExplanation(
                summary=(
                    "No component risk data is available "
                    "for this BOM."
                ),
                risk_drivers=[],
                recommendations=[
                    BOMRiskRecommendation(
                        priority=RiskSeverity.UNKNOWN,
                        component_id=None,
                        mpn=None,
                        action=(
                            "Run component enrichment and "
                            "risk analysis before making "
                            "procurement decisions."
                        ),
                        reason=(
                            "The BOM contains no persisted "
                            "component risk assessments."
                        ),
                    )
                ],
            )

        risk_drivers = (
            BOMRiskExplainer._build_risk_drivers(
                assessment
            )
        )

        recommendations = (
            BOMRiskExplainer._build_recommendations(
                assessment
            )
        )

        summary = (
            BOMRiskExplainer._build_summary(
                assessment
            )
        )

        return BOMRiskExplanation(
            summary=summary,
            risk_drivers=risk_drivers,
            recommendations=recommendations,
        )

    @staticmethod
    def _build_summary(
        assessment: BOMRiskAssessment,
    ) -> str:
        return (
            f"BOM risk is {assessment.severity.value} "
            f"with an overall score of "
            f"{assessment.overall_score:.2f}. "
            f"{assessment.high_risk_count} high-risk or "
            f"critical components were identified, "
            f"including {assessment.critical_count} "
            f"critical components."
        )

    @staticmethod
    def _build_risk_drivers(
        assessment: BOMRiskAssessment,
    ) -> list[BOMRiskDriver]:

        drivers: list[BOMRiskDriver] = []

        for component in assessment.top_risk_components:
            if component.severity not in {
                RiskSeverity.HIGH,
                RiskSeverity.CRITICAL,
            }:
                continue

            if (
                component.lifecycle_risk
                and component.availability_risk
            ):
                reason = (
                    "Component has both lifecycle and "
                    "availability risk."
                )

            elif component.lifecycle_risk:
                reason = (
                    "Component has elevated lifecycle risk."
                )

            elif component.availability_risk:
                reason = (
                    "Component has elevated availability risk."
                )

            else:
                reason = (
                    "Component has a high overall risk score."
                )

            drivers.append(
                BOMRiskDriver(
                    component_id=component.component_id,
                    mpn=component.mpn,
                    score=component.score,
                    severity=component.severity,
                    reason=reason,
                )
            )

        return drivers

    @staticmethod
    def _build_recommendations(
        assessment: BOMRiskAssessment,
    ) -> list[BOMRiskRecommendation]:

        recommendations: list[BOMRiskRecommendation] = []

        for component in assessment.top_risk_components:
            if component.severity == RiskSeverity.CRITICAL:
                if (
                    component.lifecycle_risk
                    and component.availability_risk
                ):
                    action = (
                        "Prioritize alternate-component "
                        "qualification and alternate-supplier "
                        "analysis."
                    )
                    reason = (
                        "The component has critical risk "
                        "across lifecycle and availability."
                    )

                elif component.lifecycle_risk:
                    action = (
                        "Prioritize replacement or "
                        "alternate-component qualification."
                    )
                    reason = (
                        "The component has critical lifecycle "
                        "risk."
                    )

                elif component.availability_risk:
                    action = (
                        "Identify alternate distributors "
                        "and qualify backup sourcing."
                    )
                    reason = (
                        "The component has critical "
                        "availability risk."
                    )

                else:
                    action = (
                        "Perform immediate procurement and "
                        "substitution analysis."
                    )
                    reason = (
                        "The component has critical overall "
                        "risk."
                    )

                recommendations.append(
                    BOMRiskRecommendation(
                        priority=RiskSeverity.CRITICAL,
                        component_id=component.component_id,
                        mpn=component.mpn,
                        action=action,
                        reason=reason,
                    )
                )

            elif component.severity == RiskSeverity.HIGH:
                if component.lifecycle_risk:
                    action = (
                        "Review lifecycle status and "
                        "evaluate an alternate component."
                    )
                    reason = (
                        "The component has high lifecycle risk."
                    )

                elif component.availability_risk:
                    action = (
                        "Review distributor availability and "
                        "identify backup suppliers."
                    )
                    reason = (
                        "The component has high availability risk."
                    )

                else:
                    action = (
                        "Review the component for procurement "
                        "risk and potential alternatives."
                    )
                    reason = (
                        "The component has high overall risk."
                    )

                recommendations.append(
                    BOMRiskRecommendation(
                        priority=RiskSeverity.HIGH,
                        component_id=component.component_id,
                        mpn=component.mpn,
                        action=action,
                        reason=reason,
                    )
                )

        if assessment.lifecycle_risk_count > 0:
            recommendations.append(
                BOMRiskRecommendation(
                    priority=RiskSeverity.HIGH,
                    component_id=None,
                    mpn=None,
                    action=(
                        "Review lifecycle risk across the BOM "
                        "and identify components requiring "
                        "replacement planning."
                    ),
                    reason=(
                        f"{assessment.lifecycle_risk_count} "
                        "components have lifecycle risk."
                    ),
                )
            )

        if assessment.availability_risk_count > 0:
            recommendations.append(
                BOMRiskRecommendation(
                    priority=RiskSeverity.HIGH,
                    component_id=None,
                    mpn=None,
                    action=(
                        "Review distributor coverage and "
                        "establish backup sourcing for "
                        "availability-constrained components."
                    ),
                    reason=(
                        f"{assessment.availability_risk_count} "
                        "components have availability risk."
                    ),
                )
            )

        return recommendations