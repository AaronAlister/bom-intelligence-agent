from collections.abc import Iterable

from backend.app.intelligence.availability.models import (
    AvailabilityStatus,
    AvailabilitySummary,
    DistributorAvailability,
    ProcurementStatus,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


class AvailabilityAggregator:
    """
    Aggregates distributor availability for a component.
    """

    @staticmethod
    def from_results(
        results: Iterable[ComponentEnrichmentResult],
    ) -> AvailabilitySummary:
        """
        Build an availability summary from provider results.
        """

        distributors: list[DistributorAvailability] = []

        for result in results:
            status = (
                AvailabilityAggregator._get_status(
                    result.availability
                )
            )

            distributors.append(
                DistributorAvailability(
                    distributor=result.source,
                    quantity_available=(
                        result.availability
                    ),
                    status=status,
                )
            )

        total_quantity = sum(
            availability.quantity_available or 0
            for availability in distributors
        )

        available = [
            availability
            for availability in distributors
            if availability.status
            == AvailabilityStatus.IN_STOCK
        ]

        unavailable = [
            availability
            for availability in distributors
            if availability.status
            == AvailabilityStatus.OUT_OF_STOCK
        ]

        quantities = [
            availability.quantity_available
            for availability in distributors
            if availability.quantity_available is not None
            and availability.quantity_available > 0
        ]

        best_available_quantity = (
            max(quantities)
            if quantities
            else None
        )

        procurement_status = (
            AvailabilityAggregator._get_procurement_status(
                distributors
            )
        )

        return AvailabilitySummary(
            distributors=distributors,
            total_distributor_quantity=total_quantity,
            distributors_available=len(available),
            distributors_unavailable=len(unavailable),
            best_available_quantity=(
                best_available_quantity
            ),
            procurement_status=procurement_status,
        )

    @staticmethod
    def _get_status(
        quantity: int | None,
    ) -> AvailabilityStatus:
        """
        Convert a distributor quantity into a normalized
        availability status.
        """

        if quantity is None:
            return AvailabilityStatus.UNKNOWN

        if quantity > 0:
            return AvailabilityStatus.IN_STOCK

        return AvailabilityStatus.OUT_OF_STOCK

    @staticmethod
    def _get_procurement_status(
        distributors: list[DistributorAvailability],
    ) -> ProcurementStatus:
        """
        Determine overall procurement readiness.

        Rules:

        Any positive inventory:
            READY

        No inventory, but at least one distributor reports
        zero stock:
            UNAVAILABLE

        No usable availability information:
            UNKNOWN
        """

        if any(
            distributor.status
            == AvailabilityStatus.IN_STOCK
            for distributor in distributors
        ):
            return ProcurementStatus.READY

        if any(
            distributor.status
            == AvailabilityStatus.OUT_OF_STOCK
            for distributor in distributors
        ):
            return ProcurementStatus.UNAVAILABLE

        return ProcurementStatus.UNKNOWN