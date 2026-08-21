from dataclasses import dataclass

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.pricing import (
    select_price_break,
)


@dataclass(slots=True, frozen=True)
class ComponentCost:
    """Calculated procurement cost for one component."""

    supplier: str
    mpn: str
    quantity: int

    unit_price: float | None
    total_cost: float | None
    currency: str | None


class ComponentCostCalculator:
    """
    Calculate the effective procurement cost for a component.

    Price-break pricing is applied according to the requested
    quantity. MOQ, inventory, and order-multiple constraints
    are validated before calculating cost.
    """

    def __init__(
        self,
        *,
        quantity: int,
    ) -> None:
        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero"
            )

        self.quantity = quantity

    def calculate(
        self,
        quote: SupplierQuote,
    ) -> ComponentCost:
        """Calculate effective unit and total component cost."""

        self._validate_inventory(quote)
        self._validate_moq(quote)
        self._validate_order_multiple(quote)

        unit_price, currency = (
            self._resolve_price(quote)
        )

        total_cost = (
            None
            if unit_price is None
            else round(
                unit_price * self.quantity,
                2,
            )
        )

        return ComponentCost(
            supplier=quote.supplier,
            mpn=quote.mpn,
            quantity=self.quantity,
            unit_price=unit_price,
            total_cost=total_cost,
            currency=currency,
        )

    def _resolve_price(
        self,
        quote: SupplierQuote,
    ) -> tuple[float | None, str | None]:
        """
        Resolve the effective unit price.

        Price breaks take precedence over the quote-level
        unit price.
        """

        if quote.price_breaks:
            price_break = select_price_break(
                quote.price_breaks,
                self.quantity,
            )

            if price_break is not None:
                return (
                    price_break.unit_price,
                    price_break.currency,
                )

        return (
            quote.unit_price,
            quote.currency,
        )

    def _validate_inventory(
        self,
        quote: SupplierQuote,
    ) -> None:
        """Ensure the supplier has enough inventory."""

        if quote.quantity_available is None:
            return

        if (
            quote.quantity_available
            < self.quantity
        ):
            raise ValueError(
                f"Supplier {quote.supplier} "
                f"cannot fulfill quantity "
                f"{self.quantity}"
            )

    def _validate_moq(
        self,
        quote: SupplierQuote,
    ) -> None:
        """Ensure requested quantity satisfies MOQ."""

        if quote.moq is None:
            return

        if quote.moq <= 0:
            return

        if self.quantity < quote.moq:
            raise ValueError(
                f"Requested quantity "
                f"{self.quantity} violates MOQ "
                f"{quote.moq} for "
                f"{quote.supplier}"
            )

    def _validate_order_multiple(
        self,
        quote: SupplierQuote,
    ) -> None:
        """Ensure requested quantity satisfies order multiple."""

        if quote.order_multiple is None:
            return

        if quote.order_multiple <= 0:
            raise ValueError(
                f"Invalid order multiple "
                f"for {quote.supplier}"
            )

        if (
            self.quantity
            % quote.order_multiple
            != 0
        ):
            raise ValueError(
                f"Requested quantity "
                f"{self.quantity} violates "
                f"order multiple "
                f"{quote.order_multiple} "
                f"for {quote.supplier}"
            )