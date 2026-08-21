from backend.app.intelligence.alternatives.matcher import (
    AlternativeMatcher,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


def make_component(
    *,
    mpn: str,
    manufacturer: str,
    category: str,
    package: str,
    lifecycle_status: str,
    availability: int,
) -> ComponentEnrichmentResult:
    return ComponentEnrichmentResult(
        mpn=mpn,
        manufacturer=manufacturer,
        category=category,
        package=package,
        lifecycle_status=lifecycle_status,
        availability=availability,
        source="test",
    )


def test_matching_candidate_is_ranked():
    source = make_component(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=500,
    )

    candidate = make_component(
        mpn="LM358D",
        manufacturer="STMicroelectronics",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=5000,
    )

    result = AlternativeMatcher.analyze(
        source=source,
        candidates=[candidate],
    )

    assert len(result.candidates) == 1

    alternative = result.candidates[0]

    assert alternative.component.mpn == "LM358D"
    assert alternative.category_match is True
    assert alternative.package_match is True
    assert alternative.manufacturer_match is False

    assert (
        alternative.compatibility_score
        == 90.0
    )

    assert result.best_candidate is alternative


def test_manufacturer_match_increases_score():
    source = make_component(
        mpn="SOURCE-1",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    same_manufacturer = make_component(
        mpn="ALT-1",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    different_manufacturer = make_component(
        mpn="ALT-2",
        manufacturer="STMicroelectronics",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    result = AlternativeMatcher.analyze(
        source=source,
        candidates=[
            different_manufacturer,
            same_manufacturer,
        ],
    )

    assert len(result.candidates) == 2

    assert (
        result.candidates[0].component.mpn
        == "ALT-1"
    )

    assert (
        result.candidates[0].compatibility_score
        > result.candidates[1].compatibility_score
    )


def test_incompatible_category_is_rejected():
    source = make_component(
        mpn="SOURCE-1",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    candidate = make_component(
        mpn="ALT-1",
        manufacturer="Texas Instruments",
        category="Microcontroller",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    result = AlternativeMatcher.analyze(
        source=source,
        candidates=[candidate],
    )

    assert result.candidates == []
    assert result.best_candidate is None


def test_incompatible_package_is_rejected():
    source = make_component(
        mpn="SOURCE-1",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    candidate = make_component(
        mpn="ALT-1",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="QFN-16",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    result = AlternativeMatcher.analyze(
        source=source,
        candidates=[candidate],
    )

    assert result.candidates == []
    assert result.best_candidate is None


def test_source_component_is_not_returned_as_alternative():
    source = make_component(
        mpn="SOURCE-1",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    result = AlternativeMatcher.analyze(
        source=source,
        candidates=[source],
    )

    assert result.candidates == []
    assert result.best_candidate is None


def test_candidates_are_ranked_by_score():
    source = make_component(
        mpn="SOURCE-1",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
    )

    weak = make_component(
        mpn="WEAK",
        manufacturer="Other",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="NRND",
        availability=10,
    )

    strong = make_component(
        mpn="STRONG",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=5000,
    )

    result = AlternativeMatcher.analyze(
        source=source,
        candidates=[weak, strong],
    )

    assert (
        result.candidates[0].component.mpn
        == "STRONG"
    )

    assert (
        result.candidates[1].component.mpn
        == "WEAK"
    )