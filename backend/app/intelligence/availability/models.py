from dataclasses import dataclass
from enum import StrEnum


class AvailabilityStatus(StrEnum):
    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"


class ProcurementStatus(StrEnum):
    READY = "READY"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class DistributorAvailability:
    """
    Availability information from a single distributor.
    """

    distributor: str
    quantity_available: int | None
    status: AvailabilityStatus


@dataclass(slots=True)
class AvailabilitySummary:
    """
    Aggregated availability across distributors.
    """

    distributors: list[DistributorAvailability]

    total_distributor_quantity: int
    distributors_available: int
    distributors_unavailable: int

    best_available_quantity: int | None
    procurement_status: ProcurementStatus
    