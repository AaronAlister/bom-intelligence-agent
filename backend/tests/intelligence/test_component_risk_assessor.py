from backend.app.intelligence.availability.aggregator import (
    AvailabilityAggregator,
)
from backend.app.intelligence.availability.procurement import (
    ComponentProcurementResult,
)
from backend.app.intelligence.component.models import (
    ComponentIntelligenceResult,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
    LifecycleRisk,
    LifecycleStatus,
)
from backend.app.intelligence.risk.assessor import (
    ComponentRiskAssessor,
)
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)


def make_intelligence(
    *,
    lifecycle_status: LifecycleStatus,
    availability: list[int | None],
) -> ComponentIntelligenceResult:
    from backend.app.intelligence.enrichment.models import (
        ComponentEnrichmentResult,
    )

    distributor_results = [
        ComponentEnrichmentResult(
            mpn="TEST-MPN",
            manufacturer="Test Manufacturer",
            availability=quantity,
            lifecycle_status=lifecycle_status.value,
            source=f"distributor-{index}",
        )
        for index, quantity in enumerate(
            availability,
            start=1,
        )
    ]

    availability_summary = (
        AvailabilityAggregator.from_results(
            distributor_results
        )
    )

    procurement = ComponentProcurementResult(
        mpn="TEST-MPN",
        manufacturer="Test Manufacturer",
        distributor_results=distributor_results,
        availability=availability_summary,
    )

    lifecycle = LifecycleAssessment(
        status=lifecycle_status,
        eol_date=None,
        last_buy_date=None,
        risk=(
            LifecycleRisk.LOW
            if lifecycle_status
            == LifecycleStatus.ACTIVE
            else LifecycleRisk.HIGH
        ),
        source="test",
    )

    return ComponentIntelligenceResult(
        mpn="TEST-MPN",
        manufacturer="Test Manufacturer",
        procurement=procurement,
        lifecycle=lifecycle,
    )


def test_active_component_with_multiple_distributors_is_low_risk():
    intelligence = make_intelligence(
        lifecycle_status=LifecycleStatus.ACTIVE,
        availability=[
            5000,
            4200,
            8100,
        ],
    )

    assessment = ComponentRiskAssessor.assess(
        intelligence
    )

    assert assessment.score == 0.0

    assert (
        assessment.severity
        == RiskSeverity.LOW
    )

    assert assessment.lifecycle_score == 0.0
    assert assessment.availability_score == 0.0

    assert len(assessment.reasons) == 2


def test_nrnd_component_with_single_distributor_is_high_risk():
    intelligence = make_intelligence(
        lifecycle_status=LifecycleStatus.NRND,
        availability=[
            5000,
        ],
    )

    assessment = ComponentRiskAssessor.assess(
        intelligence
    )

    # 50 * 0.60 + 50 * 0.40
    assert assessment.score == 50.0

    assert (
        assessment.severity
        == RiskSeverity.HIGH
    )

    assert assessment.lifecycle_score == 50.0
    assert assessment.availability_score == 50.0


def test_eol_component_with_multiple_distributors_remains_high_risk():
    intelligence = make_intelligence(
        lifecycle_status=LifecycleStatus.EOL,
        availability=[
            5000,
            4200,
        ],
    )

    assessment = ComponentRiskAssessor.assess(
        intelligence
    )

    # 80 * 0.60 + 0 * 0.40
    assert assessment.score == 48.0

    assert (
        assessment.severity
        == RiskSeverity.MEDIUM
    )

    assert assessment.lifecycle_score == 80.0
    assert assessment.availability_score == 0.0


def test_obsolete_component_with_no_stock_is_critical():
    intelligence = make_intelligence(
        lifecycle_status=LifecycleStatus.OBSOLETE,
        availability=[
            0,
            0,
            0,
        ],
    )

    assessment = ComponentRiskAssessor.assess(
        intelligence
    )

    # 100 * 0.60 + 80 * 0.40
    assert assessment.score == 92.0

    assert (
        assessment.severity
        == RiskSeverity.CRITICAL
    )

    assert assessment.lifecycle_score == 100.0
    assert assessment.availability_score == 80.0


def test_unknown_lifecycle_without_stock_has_medium_risk():
    intelligence = make_intelligence(
        lifecycle_status=LifecycleStatus.UNKNOWN,
        availability=[],
    )

    assessment = ComponentRiskAssessor.assess(
        intelligence
    )

    # 25 * 0.60 + 25 * 0.40
    assert assessment.score == 25.0

    assert (
        assessment.severity
        == RiskSeverity.MEDIUM
    )

    assert assessment.lifecycle_score == 25.0
    assert assessment.availability_score == 25.0