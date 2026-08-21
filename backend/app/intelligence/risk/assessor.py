from backend.app.intelligence.component.models import (
    ComponentIntelligenceResult,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleStatus,
)
from backend.app.intelligence.risk.models import (
    ComponentRiskAssessment,
    RiskSeverity,
)


class ComponentRiskAssessor:
    """
    Calculates an explainable component risk score from
    lifecycle and distributor availability intelligence.
    """

    @classmethod
    def assess(
        cls,
        intelligence: ComponentIntelligenceResult,
    ) -> ComponentRiskAssessment:
        lifecycle_score, lifecycle_reason = (
            cls._lifecycle_risk(
                intelligence
            )
        )

        availability_score, availability_reason = (
            cls._availability_risk(
                intelligence
            )
        )

        # Lifecycle is the stronger long-term risk signal.
        score = (
            lifecycle_score * 0.60
            + availability_score * 0.40
        )

        severity = cls._severity(score)

        reasons = [
            lifecycle_reason,
            availability_reason,
        ]

        return ComponentRiskAssessment(
            score=round(score, 2),
            severity=severity,
            lifecycle_score=lifecycle_score,
            availability_score=availability_score,
            reasons=reasons,
        )

    @staticmethod
    def _lifecycle_risk(
        intelligence: ComponentIntelligenceResult,
    ) -> tuple[float, str]:
        status = intelligence.lifecycle.status

        if status == LifecycleStatus.ACTIVE:
            return (
                0.0,
                "Component lifecycle is ACTIVE.",
            )

        if status == LifecycleStatus.NRND:
            return (
                50.0,
                "Component is NRND (Not Recommended for New Designs).",
            )

        if status == LifecycleStatus.EOL:
            return (
                80.0,
                "Component is End-of-Life (EOL).",
            )

        if status == LifecycleStatus.OBSOLETE:
            return (
                100.0,
                "Component is obsolete or discontinued.",
            )

        return (
            25.0,
            "Component lifecycle status is unknown.",
        )

    @staticmethod
    def _availability_risk(
        intelligence: ComponentIntelligenceResult,
    ) -> tuple[float, str]:
        availability = (
            intelligence.procurement.availability
        )

        distributor_count = len(
            availability.distributors
        )

        available_distributors = (
            availability.distributors_available
        )

        total_quantity = (
            availability.total_distributor_quantity
        )

        if distributor_count == 0:
            return (
                25.0,
                "No distributor availability data is available.",
            )

        if available_distributors >= 2:
            return (
                0.0,
                (
                    f"Component is available from "
                    f"{available_distributors} distributors "
                    f"with {total_quantity} total units reported."
                ),
            )

        if available_distributors == 1:
            return (
                50.0,
                (
                    "Component is available from only "
                    "one distributor."
                ),
            )

        return (
            80.0,
            "No distributor currently reports available stock.",
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