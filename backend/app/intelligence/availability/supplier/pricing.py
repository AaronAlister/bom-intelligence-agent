from collections.abc import Iterable

from backend.app.intelligence.availability.supplier.models import (
    PriceBreak,
)


def select_price_break(
    price_breaks: Iterable[PriceBreak],
    quantity: int,
) -> PriceBreak | None:
    """
    Select the applicable price break for a requested quantity.

    The applicable tier is the one with the highest
    minimum quantity that does not exceed the requested
    quantity.

    Example:

        1   -> tier starting at 1
        10  -> tier starting at 10
        100 -> tier starting at 100
    """

    if quantity <= 0:
        raise ValueError(
            "Quantity must be greater than zero"
        )

    applicable = [
        price_break
        for price_break in price_breaks
        if (
            price_break.min_quantity <= quantity
            and (
                price_break.max_quantity is None
                or quantity <= price_break.max_quantity
            )
        )
    ]

    if not applicable:
        return None

    return max(
        applicable,
        key=lambda price_break: (
            price_break.min_quantity
        ),
    )