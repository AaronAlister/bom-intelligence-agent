from dataclasses import dataclass

from backend.app.intelligence.availability.supplier.cost import (
    ComponentCostCalculator,
)
from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)


@dataclass(slots=True, frozen=True)
class SupplierCostOption:
    """Calculated cost for one supplier."""

    supplier: str
    mpn: str
    quantity: int

    unit_price: float | None
    total_cost: float | None
    currency: str | None


@dataclass(slots=True, frozen=True)
class CostComparison:
    """Cost comparison across suppliers."""

    mpn: str
    quantity: int

    options: list[SupplierCostOption]

    best_supplier: str
    best_unit_price: float
    best_total_cost: float

    highest_total_cost: float

    potential_savings: float
    potential_savings_percent: float

    currency: str


class CostComparisonService:
    """
    Compare procurement costs across suppliers for one component.
    """

    def __init__(
        self,
        quotes: list[SupplierQuote],
    ) -> None:
        if not quotes:
            raise ValueError(
                "At least one supplier quote is required"
            )

        self._quotes = quotes

    def compare(
        self,
        *,
        quantity: int,
    ) -> CostComparison:
        """Compare supplier costs for the requested quantity."""

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero"
            )

        options: list[SupplierCostOption] = []

        for quote in self._quotes:
            try:
                component_cost = (
                    ComponentCostCalculator(
                        quantity=quantity
                    ).calculate(quote)
                )
            except ValueError:
                # A supplier that cannot fulfill the requested
                # quantity is not a viable cost option.
                continue

            options.append(
                SupplierCostOption(
                    supplier=component_cost.supplier,
                    mpn=component_cost.mpn,
                    quantity=component_cost.quantity,
                    unit_price=component_cost.unit_price,
                    total_cost=component_cost.total_cost,
                    currency=component_cost.currency,
                )
            )

        if not options:
            raise ValueError(
                "No supplier has a calculable cost"
            )

        self._validate_currency(options)

        priced_options = [
            (
                option,
                option.total_cost,
            )
            for option in options
            if option.total_cost is not None
            and option.unit_price is not None
        ]

        if not priced_options:
            raise ValueError(
                "No supplier has a calculable cost"
            )

        best_option, best_total_cost = min(
            priced_options,
            key=lambda item: item[1],
        )

        highest_total_cost = max(
            total_cost
            for _, total_cost in priced_options
        )

        potential_savings = round(
            highest_total_cost
            - best_total_cost,
            2,
        )

        potential_savings_percent = (
            0.0
            if highest_total_cost == 0
            else round(
                (
                    potential_savings
                    / highest_total_cost
                )
                * 100,
                6,
            )
        )

        currency = best_option.currency

        if currency is None:
            raise ValueError(
                "Supplier costs must have a currency"
            )

        if best_option.unit_price is None:
            raise ValueError(
                "Best supplier has no unit price"
            )

        return CostComparison(
            mpn=best_option.mpn,
            quantity=quantity,
            options=options,
            best_supplier=best_option.supplier,
            best_unit_price=best_option.unit_price,
            best_total_cost=best_total_cost,
            highest_total_cost=highest_total_cost,
            potential_savings=potential_savings,
            potential_savings_percent=(
                potential_savings_percent
            ),
            currency=currency,
        )

    @staticmethod
    def _validate_currency(
        options: list[SupplierCostOption],
    ) -> None:
        """Ensure priced supplier options use one currency."""

        currencies = {
            option.currency
            for option in options
            if option.total_cost is not None
            and option.currency is not None
        }

        if len(currencies) > 1:
            raise ValueError(
                "Supplier costs must use the same "
                "currency"
            )