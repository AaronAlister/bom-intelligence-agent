from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.lifecycle.assessor import (
    LifecycleAssessor,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleRisk,
    LifecycleStatus,
)


def test_active_component_has_low_lifecycle_risk():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            lifecycle_status="ACTIVE",
            source="mouser",
        ),
    ]

    assessment = LifecycleAssessor.assess(
        results
    )

    assert (
        assessment.status
        == LifecycleStatus.ACTIVE
    )

    assert (
        assessment.risk
        == LifecycleRisk.LOW
    )

    assert assessment.source == "mouser"


def test_nrnd_component_has_medium_lifecycle_risk():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            lifecycle_status="NRND",
            source="arrow",
        ),
    ]

    assessment = LifecycleAssessor.assess(
        results
    )

    assert (
        assessment.status
        == LifecycleStatus.NRND
    )

    assert (
        assessment.risk
        == LifecycleRisk.MEDIUM
    )


def test_eol_component_has_high_lifecycle_risk():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            lifecycle_status="EOL",
            source="digikey",
        ),
    ]

    assessment = LifecycleAssessor.assess(
        results
    )

    assert (
        assessment.status
        == LifecycleStatus.EOL
    )

    assert (
        assessment.risk
        == LifecycleRisk.HIGH
    )


def test_obsolete_component_has_critical_risk():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            lifecycle_status="OBSOLETE",
            source="mouser",
        ),
    ]

    assessment = LifecycleAssessor.assess(
        results
    )

    assert (
        assessment.status
        == LifecycleStatus.OBSOLETE
    )

    assert (
        assessment.risk
        == LifecycleRisk.CRITICAL
    )


def test_unknown_lifecycle_is_unknown_risk():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            lifecycle_status=None,
            source="mouser",
        ),
    ]

    assessment = LifecycleAssessor.assess(
        results
    )

    assert (
        assessment.status
        == LifecycleStatus.UNKNOWN
    )

    assert (
        assessment.risk
        == LifecycleRisk.UNKNOWN
    )

    assert assessment.source is None


def test_assessor_uses_first_recognized_provider_status():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            lifecycle_status=None,
            source="mouser",
        ),
        ComponentEnrichmentResult(
            mpn="LM358DR",
            lifecycle_status="ACTIVE",
            source="arrow",
        ),
        ComponentEnrichmentResult(
            mpn="LM358DR",
            lifecycle_status="EOL",
            source="digikey",
        ),
    ]

    assessment = LifecycleAssessor.assess(
        results
    )

    assert (
        assessment.status
        == LifecycleStatus.ACTIVE
    )

    assert assessment.source == "arrow"