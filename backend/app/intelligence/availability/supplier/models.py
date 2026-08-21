from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class PriceBreak:
    """
    Quantity-based supplier pricing tier.

    A price break applies when the requested quantity
    falls within the specified quantity range.
    """

    min_quantity: int
    unit_price: float
    currency: str
    max_quantity: int | None = None


@dataclass(slots=True)
class SupplierQuote:
    """
    Normalized commercial procurement information
    returned by a supplier.
    """

    supplier: str
    manufacturer: str | None
    mpn: str

    unit_price: float | None = None
    currency: str | None = None

    quantity_available: int | None = None

    moq: int | None = None
    order_multiple: int | None = None

    lead_time_days: int | None = None

    price_breaks: list[PriceBreak] = field(
        default_factory=list
    )

    source: str = "unknown"