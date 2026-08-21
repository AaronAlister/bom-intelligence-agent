from dataclasses import dataclass

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)


@dataclass(slots=True, frozen=True)
class SupplierScore:
    """Explainable supplier procurement score."""

    supplier: str
    total_score: float

    price_score: float
    availability_score: float
    lead_time_score: float
    moq_score: float
    order_multiple_score: float


class SupplierScorer:
    """
    Score supplier quotes for a requested procurement quantity.

    Maximum score: 100 points.

    Weights:
        Price:             35
        Availability:     25
        Lead time:        20
        MOQ:              10
        Order multiple:  10
    """

    PRICE_WEIGHT = 35.0
    AVAILABILITY_WEIGHT = 25.0
    LEAD_TIME_WEIGHT = 20.0
    MOQ_WEIGHT = 10.0
    ORDER_MULTIPLE_WEIGHT = 10.0

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

    def score(
        self,
        quote: SupplierQuote,
        quotes: list[SupplierQuote],
    ) -> SupplierScore:
        """
        Calculate an explainable score for one supplier.

        Scores are normalized relative to the supplied
        supplier quote set.
        """

        price_score = (
            self._price_score(
                quote,
                quotes,
            )
        )

        availability_score = (
            self._availability_score(
                quote,
                quotes,
            )
        )

        lead_time_score = (
            self._lead_time_score(
                quote,
                quotes,
            )
        )

        moq_score = self._moq_score(quote)

        order_multiple_score = (
            self._order_multiple_score(quote)
        )

        total_score = (
            price_score
            + availability_score
            + lead_time_score
            + moq_score
            + order_multiple_score
        )

        return SupplierScore(
            supplier=quote.supplier,
            total_score=round(
                min(100.0, max(0.0, total_score)),
                2,
            ),
            price_score=round(
                price_score,
                2,
            ),
            availability_score=round(
                availability_score,
                2,
            ),
            lead_time_score=round(
                lead_time_score,
                2,
            ),
            moq_score=round(
                moq_score,
                2,
            ),
            order_multiple_score=round(
                order_multiple_score,
                2,
            ),
        )

    def _price_score(
        self,
        quote: SupplierQuote,
        quotes: list[SupplierQuote],
    ) -> float:
        """Score price relative to the cheapest available quote."""

        prices = [
            q.unit_price
            for q in quotes
            if q.unit_price is not None
            and q.unit_price > 0
        ]

        if quote.unit_price is None:
            return 0.0

        if not prices:
            return 0.0

        cheapest = min(prices)

        if cheapest <= 0:
            return 0.0

        return (
            cheapest
            / quote.unit_price
            * self.PRICE_WEIGHT
        )

    def _availability_score(
        self,
        quote: SupplierQuote,
        quotes: list[SupplierQuote],
    ) -> float:
        """Score inventory relative to the best supplier."""

        quantities = [
            q.quantity_available
            for q in quotes
            if q.quantity_available is not None
            and q.quantity_available > 0
        ]

        if quote.quantity_available is None:
            return 0.0

        if not quantities:
            return 0.0

        maximum = max(quantities)

        if maximum <= 0:
            return 0.0

        return (
            quote.quantity_available
            / maximum
            * self.AVAILABILITY_WEIGHT
        )

    def _lead_time_score(
        self,
        quote: SupplierQuote,
        quotes: list[SupplierQuote],
    ) -> float:
        """Score shorter lead times higher."""

        lead_times = [
            q.lead_time_days
            for q in quotes
            if q.lead_time_days is not None
            and q.lead_time_days > 0
        ]

        if quote.lead_time_days is None:
            return 0.0

        if not lead_times:
            return 0.0

        fastest = min(lead_times)

        if fastest <= 0:
            return 0.0

        return (
            fastest
            / quote.lead_time_days
            * self.LEAD_TIME_WEIGHT
        )

    def _moq_score(
        self,
        quote: SupplierQuote,
    ) -> float:
        """
        Score MOQ suitability.

        Full score when the requested quantity satisfies MOQ.
        Zero when MOQ exceeds requested quantity.
        """

        if quote.moq is None:
            return 0.0

        if quote.moq <= 0:
            return 0.0

        if self.quantity < quote.moq:
            return 0.0

        return self.MOQ_WEIGHT

    def _order_multiple_score(
        self,
        quote: SupplierQuote,
    ) -> float:
        """
        Score order-multiple compatibility.

        Full score when requested quantity is an exact
        multiple of the supplier's order multiple.
        """

        if quote.order_multiple is None:
            return 0.0

        if quote.order_multiple <= 0:
            return 0.0

        if (
            self.quantity
            % quote.order_multiple
            == 0
        ):
            return self.ORDER_MULTIPLE_WEIGHT

        return 0.0