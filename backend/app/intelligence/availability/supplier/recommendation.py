from dataclasses import dataclass

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.scoring import (
    SupplierScore,
)
from backend.app.intelligence.availability.supplier.selection import (
    SupplierSelection,
    SupplierSelector,
)


@dataclass(slots=True, frozen=True)
class ProcurementRecommendation:
    """Explainable procurement recommendation."""

    action: str
    supplier: str
    score: SupplierScore
    alternatives: list[SupplierScore]
    reason: str


class ProcurementRecommendationService:
    """
    Converts supplier selection into a procurement recommendation.

    Current supported action:

        BUY

    The service deliberately keeps recommendation logic
    separate from supplier scoring and selection.
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

    def recommend(
        self,
        quotes: list[SupplierQuote],
    ) -> ProcurementRecommendation:
        """
        Select the best eligible supplier and produce
        an actionable procurement recommendation.
        """

        if not quotes:
            raise ValueError(
                "At least one supplier quote is required"
            )

        selector = SupplierSelector(
            quantity=self.quantity
        )

        selection: SupplierSelection = (
            selector.select(quotes)
        )

        selected_score = selection.selected_score

        alternatives = [
            score
            for score in selection.ranked_suppliers
            if score.supplier
            != selection.selected_supplier
        ]

        return ProcurementRecommendation(
            action="BUY",
            supplier=selection.selected_supplier,
            score=selected_score,
            alternatives=alternatives,
            reason=selection.recommendation_reason,
        )