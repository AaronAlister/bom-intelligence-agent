from backend.app.intelligence.availability.aggregator import (
    AvailabilityAggregator,
)
from backend.app.intelligence.availability.models import (
    AvailabilityStatus,
    ProcurementStatus,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


def test_aggregates_multiple_distributors():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            source="mouser",
            availability=5000,
        ),
        ComponentEnrichmentResult(
            mpn="LM358DR",
            source="arrow",
            availability=4200,
        ),
        ComponentEnrichmentResult(
            mpn="LM358DR",
            source="digikey",
            availability=8100,
        ),
    ]

    summary = AvailabilityAggregator.from_results(
        results
    )

    assert len(summary.distributors) == 3

    assert (
        summary.total_distributor_quantity
        == 17300
    )

    assert summary.distributors_available == 3

    assert summary.distributors_unavailable == 0

    assert summary.best_available_quantity == 8100

    assert (
        summary.procurement_status
        == ProcurementStatus.READY
    )


def test_zero_quantity_is_out_of_stock():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            source="mouser",
            availability=0,
        ),
    ]

    summary = AvailabilityAggregator.from_results(
        results
    )

    assert len(summary.distributors) == 1

    distributor = summary.distributors[0]

    assert (
        distributor.status
        == AvailabilityStatus.OUT_OF_STOCK
    )

    assert (
        summary.total_distributor_quantity
        == 0
    )

    assert (
        summary.procurement_status
        == ProcurementStatus.UNAVAILABLE
    )


def test_none_quantity_is_unknown():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            source="mouser",
            availability=None,
        ),
    ]

    summary = AvailabilityAggregator.from_results(
        results
    )

    distributor = summary.distributors[0]

    assert (
        distributor.status
        == AvailabilityStatus.UNKNOWN
    )

    assert (
        summary.total_distributor_quantity
        == 0
    )

    assert (
        summary.best_available_quantity
        is None
    )

    assert (
        summary.procurement_status
        == ProcurementStatus.UNKNOWN
    )


def test_mixed_available_and_unavailable():
    results = [
        ComponentEnrichmentResult(
            mpn="LM358DR",
            source="mouser",
            availability=5000,
        ),
        ComponentEnrichmentResult(
            mpn="LM358DR",
            source="arrow",
            availability=0,
        ),
        ComponentEnrichmentResult(
            mpn="LM358DR",
            source="digikey",
            availability=None,
        ),
    ]

    summary = AvailabilityAggregator.from_results(
        results
    )

    assert (
        summary.total_distributor_quantity
        == 5000
    )

    assert summary.distributors_available == 1

    assert summary.distributors_unavailable == 1

    assert summary.best_available_quantity == 5000

    assert (
        summary.procurement_status
        == ProcurementStatus.READY
    )