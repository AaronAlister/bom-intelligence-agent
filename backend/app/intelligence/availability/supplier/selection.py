from dataclasses import dataclass

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.scoring import (
    SupplierScore,
    SupplierScorer,
)


@dataclass(slots=True, frozen=True)
class SupplierSelection:
    """Result of supplier selection for a procurement request."""

    selected_supplier: str
    selected_score: SupplierScore

    ranked_suppliers: list[SupplierScore]

    recommendation_reason: str


class SupplierSelector:
    """
    Select the best supplier for a requested quantity.

    Selection is based on the explainable SupplierScorer.
    Suppliers that cannot satisfy the requested quantity
    are excluded before scoring.
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

    def select(
        self,
        quotes: list[SupplierQuote],
    ) -> SupplierSelection:
        """
        Rank suppliers and return the highest-scoring option.
        """

        if not quotes:
            raise ValueError(
                "At least one supplier quote is required"
            )

        eligible_quotes = [
            quote
            for quote in quotes
            if self._is_eligible(quote)
        ]

        if not eligible_quotes:
            raise ValueError(
                "No supplier can satisfy the requested quantity"
            )

        scorer = SupplierScorer(
            quantity=self.quantity
        )

        scores = [
            scorer.score(
                quote,
                eligible_quotes,
            )
            for quote in eligible_quotes
        ]

        # Stable deterministic ordering:
        # total score descending, supplier name ascending.
        scores.sort(
            key=lambda score: (
                -score.total_score,
                score.supplier,
            )
        )

        selected_score = scores[0]

        return SupplierSelection(
            selected_supplier=(
                selected_score.supplier
            ),
            selected_score=selected_score,
            ranked_suppliers=scores,
            recommendation_reason=(
                self._build_recommendation_reason(
                    selected_score
                )
            ),
        )

    def _is_eligible(
        self,
        quote: SupplierQuote,
    ) -> bool:
        """
        Determine whether a supplier can fulfill
        the requested quantity.
        """

        if quote.quantity_available is not None:
            if (
                quote.quantity_available
                < self.quantity
            ):
                return False

        if quote.moq is not None:
            if (
                quote.moq > self.quantity
            ):
                return False

        if quote.order_multiple is not None:
            if quote.order_multiple <= 0:
                return False

            if (
                self.quantity
                % quote.order_multiple
                != 0
            ):
                return False

        return True

    @staticmethod
    def _build_recommendation_reason(
        score: SupplierScore,
    ) -> str:
        """Generate an explainable recommendation summary."""

        components = [
            (
                "price",
                score.price_score,
            ),
            (
                "availability",
                score.availability_score,
            ),
            (
                "lead time",
                score.lead_time_score,
            ),
            (
                "MOQ",
                score.moq_score,
            ),
            (
                "order multiple",
                score.order_multiple_score,
            ),
        ]

        strongest = sorted(
            components,
            key=lambda item: item[1],
            reverse=True,
        )

        top_factors = [
            name
            for name, value in strongest[:2]
            if value > 0
        ]

        if not top_factors:
            return (
                f"{score.supplier} selected with "
                f"a score of {score.total_score:.2f}/100."
            )

        factors = " and ".join(
            top_factors
        )

        return (
            f"{score.supplier} selected with "
            f"a score of {score.total_score:.2f}/100, "
            f"driven primarily by {factors}."
        )