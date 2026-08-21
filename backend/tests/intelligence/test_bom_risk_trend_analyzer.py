from datetime import datetime, timezone

from backend.app.intelligence.risk.bom_trend_analyzer import (
    BOMRiskTrendAnalyzer,
)
from backend.app.intelligence.risk.bom_trend_models import (
    RiskTrend,
)
from backend.app.intelligence.risk.models import RiskSeverity
from backend.app.models.bom_risk import BOMRiskRecord


def make_record(
    *,
    record_id: int,
    score: float,
    severity: str,
    high_risk_count: int,
    critical_count: int,
    lifecycle_risk_count: int,
    availability_risk_count: int,
    second: int,
) -> BOMRiskRecord:
    record = BOMRiskRecord(
        id=record_id,
        bom_id=1,
        overall_score=score,
        severity=severity,
        component_count=10,
        high_risk_count=high_risk_count,
        critical_count=critical_count,
        lifecycle_risk_count=lifecycle_risk_count,
        availability_risk_count=availability_risk_count,
    )

    record.created_at = datetime(
        2026,
        8,
        12,
        10,
        0,
        second,
        tzinfo=timezone.utc,
    )

    return record


def test_empty_history_returns_unknown():
    result = BOMRiskTrendAnalyzer.analyze([])

    assert result.trend == RiskTrend.UNKNOWN
    assert result.snapshot_count == 0

    assert result.previous_score is None
    assert result.current_score is None
    assert result.score_change is None

    assert (
        result.previous_severity
        == RiskSeverity.UNKNOWN
    )

    assert (
        result.current_severity
        == RiskSeverity.UNKNOWN
    )


def test_single_snapshot_returns_stable():
    record = make_record(
        record_id=1,
        score=40.0,
        severity="MEDIUM",
        high_risk_count=1,
        critical_count=0,
        lifecycle_risk_count=1,
        availability_risk_count=0,
        second=0,
    )

    result = BOMRiskTrendAnalyzer.analyze(
        [record]
    )

    assert result.trend == RiskTrend.STABLE
    assert result.snapshot_count == 1

    assert result.previous_score is None
    assert result.current_score == 40.0
    assert result.score_change is None

    assert (
        result.current_severity
        == RiskSeverity.MEDIUM
    )

    assert result.current_high_risk_count == 1
    assert result.current_critical_count == 0
    assert result.current_lifecycle_risk_count == 1
    assert result.current_availability_risk_count == 0


def test_worsening_risk_is_detected():
    first = make_record(
        record_id=1,
        score=20.0,
        severity="LOW",
        high_risk_count=0,
        critical_count=0,
        lifecycle_risk_count=0,
        availability_risk_count=0,
        second=0,
    )

    second = make_record(
        record_id=2,
        score=60.0,
        severity="HIGH",
        high_risk_count=3,
        critical_count=1,
        lifecycle_risk_count=2,
        availability_risk_count=1,
        second=10,
    )

    result = BOMRiskTrendAnalyzer.analyze(
        [second, first]
    )

    assert result.trend == RiskTrend.WORSENING

    assert result.snapshot_count == 2

    assert result.previous_score == 20.0
    assert result.current_score == 60.0
    assert result.score_change == 40.0

    assert (
        result.previous_severity
        == RiskSeverity.LOW
    )

    assert (
        result.current_severity
        == RiskSeverity.HIGH
    )

    assert result.high_risk_count_change == 3
    assert result.critical_count_change == 1
    assert result.lifecycle_risk_count_change == 2
    assert result.availability_risk_count_change == 1


def test_improving_risk_is_detected():
    first = make_record(
        record_id=1,
        score=80.0,
        severity="CRITICAL",
        high_risk_count=4,
        critical_count=2,
        lifecycle_risk_count=3,
        availability_risk_count=2,
        second=0,
    )

    second = make_record(
        record_id=2,
        score=30.0,
        severity="MEDIUM",
        high_risk_count=1,
        critical_count=0,
        lifecycle_risk_count=1,
        availability_risk_count=0,
        second=10,
    )

    result = BOMRiskTrendAnalyzer.analyze(
        [first, second]
    )

    assert result.trend == RiskTrend.IMPROVING

    assert result.score_change == -50.0

    assert (
        result.previous_severity
        == RiskSeverity.CRITICAL
    )

    assert (
        result.current_severity
        == RiskSeverity.MEDIUM
    )

    assert result.high_risk_count_change == -3
    assert result.critical_count_change == -2
    assert result.lifecycle_risk_count_change == -2
    assert result.availability_risk_count_change == -2


def test_small_score_change_is_stable():
    first = make_record(
        record_id=1,
        score=50.0,
        severity="HIGH",
        high_risk_count=2,
        critical_count=0,
        lifecycle_risk_count=1,
        availability_risk_count=1,
        second=0,
    )

    second = make_record(
        record_id=2,
        score=54.0,
        severity="HIGH",
        high_risk_count=2,
        critical_count=0,
        lifecycle_risk_count=1,
        availability_risk_count=1,
        second=10,
    )

    result = BOMRiskTrendAnalyzer.analyze(
        [first, second]
    )

    assert result.trend == RiskTrend.STABLE
    assert result.score_change == 4.0


def test_records_are_sorted_chronologically():
    older = make_record(
        record_id=10,
        score=20.0,
        severity="LOW",
        high_risk_count=0,
        critical_count=0,
        lifecycle_risk_count=0,
        availability_risk_count=0,
        second=0,
    )

    newer = make_record(
        record_id=11,
        score=90.0,
        severity="CRITICAL",
        high_risk_count=4,
        critical_count=2,
        lifecycle_risk_count=3,
        availability_risk_count=2,
        second=10,
    )

    result = BOMRiskTrendAnalyzer.analyze(
        [newer, older]
    )

    assert result.previous_score == 20.0
    assert result.current_score == 90.0
    assert result.score_change == 70.0
    assert result.trend == RiskTrend.WORSENING