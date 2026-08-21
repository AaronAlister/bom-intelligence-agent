from dataclasses import dataclass

from backend.app.intelligence.availability.supplier.cost import (
    ComponentCostCalculator,
)
from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)


@dataclass(slots=True, frozen=True)
class BOMComponentCost:
    """Cost breakdown for one BOM component."""

    supplier: str
    mpn: str
    quantity: int

    unit_price: float | None
    total_cost: float | None
    currency: str | None


@dataclass(slots=True, frozen=True)
class BOMCost:
    """Aggregated cost intelligence for an entire BOM."""

    components: list[BOMComponentCost]
    total_cost: float | None
    currency: str | None


class BOMCostCalculator:
    """
    Calculate the procurement cost of an entire BOM.

    Each BOM component is represented by a supplier quote
    and the required quantity.
    """

    def __init__(
        self,
        components: list[
            tuple[SupplierQuote, int]
        ],
    ) -> None:
        if not components:
            raise ValueError(
                "At least one BOM component is required"
            )

        for _, quantity in components:
            if quantity <= 0:
                raise ValueError(
                    "Quantity must be greater than zero"
                )

        self._components = components

    def calculate(self) -> BOMCost:
        """Calculate component-level and total BOM cost."""

        component_costs: list[
            BOMComponentCost
        ] = []

        currency: str | None = None
        total_cost = 0.0
        has_missing_cost = False

        for quote, quantity in self._components:
            component_cost = (
                ComponentCostCalculator(
                    quantity=quantity
                ).calculate(quote)
            )

            component = BOMComponentCost(
                supplier=component_cost.supplier,
                mpn=component_cost.mpn,
                quantity=component_cost.quantity,
                unit_price=component_cost.unit_price,
                total_cost=component_cost.total_cost,
                currency=component_cost.currency,
            )

            component_costs.append(component)

            self._validate_currency(
                currency=currency,
                component_currency=component.currency,
            )

            if currency is None:
                currency = component.currency

            if component.total_cost is None:
                has_missing_cost = True
            else:
                total_cost += component.total_cost

        return BOMCost(
            components=component_costs,
            total_cost=(
                None
                if has_missing_cost
                else round(total_cost, 2)
            ),
            currency=currency,
        )

    @staticmethod
    def _validate_currency(
        *,
        currency: str | None,
        component_currency: str | None,
    ) -> None:
        """
        Ensure all priced components use the same currency.
        """

        if (
            currency is not None
            and component_currency is not None
            and currency != component_currency
        ):
            raise ValueError(
                "BOM components must use the same "
                "currency"
            )