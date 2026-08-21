from backend.app.intelligence.risk.bom_models import (
    BOMComponentRisk,
    BOMRiskAssessment,
)
from backend.app.intelligence.risk.models import (
    ComponentRiskAssessment,
    RiskSeverity,
)


class BOMRiskAssessor:
    """
    Aggregates component-level risk into a BOM-level risk profile.
    """

    @staticmethod
    def assess(
        component_risks: list[BOMComponentRisk],
    ) -> BOMRiskAssessment:
        """
        Aggregate component risks into a BOM risk assessment.
        """

        if not component_risks:
            return BOMRiskAssessment(
                overall_score=0.0,
                severity=RiskSeverity.UNKNOWN,
                component_count=0,
                high_risk_count=0,
                critical_count=0,
                lifecycle_risk_count=0,
                availability_risk_count=0,
                top_risk_components=[],
            )

        component_count = len(component_risks)

        overall_score = (
            sum(
                risk.score
                for risk in component_risks
            )
            / component_count
        )

        high_risk_count = sum(
            1
            for risk in component_risks
            if risk.severity
            in {
                RiskSeverity.HIGH,
                RiskSeverity.CRITICAL,
            }
        )

        critical_count = sum(
            1
            for risk in component_risks
            if risk.severity
            == RiskSeverity.CRITICAL
        )

        top_risk_components = sorted(
            component_risks,
            key=lambda risk: risk.score,
            reverse=True,
        )[:10]

        severity = (
            BOMRiskAssessor._severity(
                overall_score
            )
        )
        lifecycle_risk_count = sum(
            1
            for risk in component_risks
            if risk.lifecycle_risk
        )

        availability_risk_count = sum(
            1
            for risk in component_risks
            if risk.availability_risk
        )

        return BOMRiskAssessment(
            overall_score=round(
                overall_score,
                2,
            ),
            severity=severity,
            component_count=component_count,
            high_risk_count=high_risk_count,
            critical_count=critical_count,
            lifecycle_risk_count=lifecycle_risk_count,
            availability_risk_count=availability_risk_count,
            top_risk_components=top_risk_components,
        )

    @staticmethod
    def _severity(
        score: float,
    ) -> RiskSeverity:

        if score < 20:
            return RiskSeverity.LOW

        if score < 50:
            return RiskSeverity.MEDIUM

        if score < 75:
            return RiskSeverity.HIGH

        return RiskSeverity.CRITICAL