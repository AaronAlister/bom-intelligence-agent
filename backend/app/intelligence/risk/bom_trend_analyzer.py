from collections.abc import Sequence

from backend.app.intelligence.risk.bom_trend_models import (
    BOMRiskTrend,
    RiskTrend,
)
from backend.app.intelligence.risk.models import RiskSeverity
from backend.app.models.bom_risk import BOMRiskRecord


class BOMRiskTrendAnalyzer:
    """
    Calculates BOM risk trends from historical risk snapshots.
    """

    @staticmethod
    def analyze(
        records: Sequence[BOMRiskRecord],
    ) -> BOMRiskTrend:
        """
        Analyze historical BOM risk records.

        Records may be supplied in any order. The analyzer
        uses the records chronologically based on created_at
        and id.
        """

        if not records:
            return BOMRiskTrend(
                trend=RiskTrend.UNKNOWN,
                snapshot_count=0,
                previous_score=None,
                current_score=None,
                score_change=None,
                previous_severity=RiskSeverity.UNKNOWN,
                current_severity=RiskSeverity.UNKNOWN,
                previous_high_risk_count=None,
                current_high_risk_count=None,
                high_risk_count_change=None,
                previous_critical_count=None,
                current_critical_count=None,
                critical_count_change=None,
                previous_lifecycle_risk_count=None,
                current_lifecycle_risk_count=None,
                lifecycle_risk_count_change=None,
                previous_availability_risk_count=None,
                current_availability_risk_count=None,
                availability_risk_count_change=None,
            )

        ordered = sorted(
            records,
            key=lambda record: (
                record.created_at,
                record.id,
            ),
        )

        current = ordered[-1]

        try:
            current_severity = RiskSeverity(
                current.severity
            )
        except ValueError:
            current_severity = RiskSeverity.UNKNOWN

        if len(ordered) == 1:
            return BOMRiskTrend(
                trend=RiskTrend.STABLE,
                snapshot_count=1,
                previous_score=None,
                current_score=current.overall_score,
                score_change=None,
                previous_severity=RiskSeverity.UNKNOWN,
                current_severity=current_severity,
                previous_high_risk_count=None,
                current_high_risk_count=current.high_risk_count,
                high_risk_count_change=None,
                previous_critical_count=None,
                current_critical_count=current.critical_count,
                critical_count_change=None,
                previous_lifecycle_risk_count=None,
                current_lifecycle_risk_count=(
                    current.lifecycle_risk_count
                ),
                lifecycle_risk_count_change=None,
                previous_availability_risk_count=None,
                current_availability_risk_count=(
                    current.availability_risk_count
                ),
                availability_risk_count_change=None,
            )

        previous = ordered[-2]

        try:
            previous_severity = RiskSeverity(
                previous.severity
            )
        except ValueError:
            previous_severity = RiskSeverity.UNKNOWN

        score_change = round(
            current.overall_score
            - previous.overall_score,
            2,
        )

        high_risk_count_change = (
            current.high_risk_count
            - previous.high_risk_count
        )

        critical_count_change = (
            current.critical_count
            - previous.critical_count
        )

        lifecycle_risk_count_change = (
            current.lifecycle_risk_count
            - previous.lifecycle_risk_count
        )

        availability_risk_count_change = (
            current.availability_risk_count
            - previous.availability_risk_count
        )

        trend = (
            BOMRiskTrendAnalyzer._classify_trend(
                score_change
            )
        )

        return BOMRiskTrend(
            trend=trend,
            snapshot_count=len(ordered),
            previous_score=previous.overall_score,
            current_score=current.overall_score,
            score_change=score_change,
            previous_severity=previous_severity,
            current_severity=current_severity,
            previous_high_risk_count=(
                previous.high_risk_count
            ),
            current_high_risk_count=(
                current.high_risk_count
            ),
            high_risk_count_change=(
                high_risk_count_change
            ),
            previous_critical_count=(
                previous.critical_count
            ),
            current_critical_count=(
                current.critical_count
            ),
            critical_count_change=(
                critical_count_change
            ),
            previous_lifecycle_risk_count=(
                previous.lifecycle_risk_count
            ),
            current_lifecycle_risk_count=(
                current.lifecycle_risk_count
            ),
            lifecycle_risk_count_change=(
                lifecycle_risk_count_change
            ),
            previous_availability_risk_count=(
                previous.availability_risk_count
            ),
            current_availability_risk_count=(
                current.availability_risk_count
            ),
            availability_risk_count_change=(
                availability_risk_count_change
            ),
        )

    @staticmethod
    def _classify_trend(
        score_change: float,
    ) -> str:
        """
        Classify risk movement from score change.

        A small change is considered stable to avoid
        reporting insignificant fluctuations as a trend.
        """

        if score_change > 5.0:
            return RiskTrend.WORSENING

        if score_change < -5.0:
            return RiskTrend.IMPROVING

        return RiskTrend.STABLE