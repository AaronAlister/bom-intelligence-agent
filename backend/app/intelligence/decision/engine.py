from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.recommendation import (
    ProcurementRecommendationService,
)
from backend.app.intelligence.decision.models import (
    ComponentDecision,
    DecisionAction,
    DecisionFactor,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
)
from backend.app.intelligence.risk.models import (
    ComponentRiskAssessment,
)


class ComponentDecisionEngine:
    """
    Converts component intelligence into a final procurement decision.

    The engine does not calculate risk, supplier scores, or pricing
    itself. It consumes the outputs of those specialized services
    and converts them into one explainable decision.
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

    def decide(
        self,
        *,
        mpn: str,
        manufacturer: str | None,
        quotes: list[SupplierQuote],
        risk: ComponentRiskAssessment | None = None,
        lifecycle: LifecycleAssessment | None = None,
    ) -> ComponentDecision:
        """
        Produce a procurement decision for one component.

        Decision hierarchy:

        1. Critical risk -> REVIEW
        2. High lifecycle risk -> REVIEW
        3. No eligible supplier -> SOURCE_ALTERNATIVE
        4. Otherwise -> BUY
        """

        factors: list[DecisionFactor] = []

        if risk is not None:
            factors.append(
                DecisionFactor(
                    name="risk",
                    value=f"{risk.score:.2f}",
                    impact=risk.severity.value,
                )
            )

        if lifecycle is not None:
            factors.append(
                DecisionFactor(
                    name="lifecycle",
                    value=lifecycle.status.value,
                    impact=lifecycle.risk.value,
                )
            )

        recommendation = None

        if quotes:
            try:
                recommendation = (
                    ProcurementRecommendationService(
                        quantity=self.quantity
                    ).recommend(quotes)
                )
            except ValueError:
                recommendation = None

        if recommendation is None:
            factors.append(
                DecisionFactor(
                    name="supplier",
                    value="none",
                    impact="negative",
                )
            )

            return ComponentDecision(
                mpn=mpn,
                manufacturer=manufacturer,
                action=DecisionAction.SOURCE_ALTERNATIVE,
                supplier=None,
                supplier_score=None,
                risk_score=(
                    risk.score
                    if risk is not None
                    else None
                ),
                lifecycle_status=(
                    lifecycle.status.value
                    if lifecycle is not None
                    else None
                ),
                availability=None,
                estimated_unit_price=None,
                estimated_total_cost=None,
                currency=None,
                factors=factors,
                reason=(
                    "No eligible supplier can fulfill "
                    "the requested quantity."
                ),
            )

        selected_supplier = recommendation.supplier
        selected_score = recommendation.score

        selected_quote = next(
            (
                quote
                for quote in quotes
                if quote.supplier
                == selected_supplier
            ),
            None,
        )

        availability = (
            selected_quote.quantity_available
            if selected_quote is not None
            else None
        )

        unit_price = (
            selected_quote.unit_price
            if selected_quote is not None
            else None
        )

        currency = (
            selected_quote.currency
            if selected_quote is not None
            else None
        )

        estimated_total_cost = (
            unit_price * self.quantity
            if unit_price is not None
            else None
        )

        factors.append(
            DecisionFactor(
                name="supplier",
                value=selected_supplier,
                impact="positive",
            )
        )

        factors.append(
            DecisionFactor(
                name="supplier_score",
                value=f"{selected_score.total_score:.2f}",
                impact="positive",
            )
        )

        if risk is not None:
            if risk.severity.value in {
                "HIGH",
                "CRITICAL",
            }:
                return ComponentDecision(
                    mpn=mpn,
                    manufacturer=manufacturer,
                    action=DecisionAction.REVIEW,
                    supplier=selected_supplier,
                    supplier_score=(
                        selected_score.total_score
                    ),
                    risk_score=risk.score,
                    lifecycle_status=(
                        lifecycle.status.value
                        if lifecycle is not None
                        else None
                    ),
                    availability=availability,
                    estimated_unit_price=unit_price,
                    estimated_total_cost=(
                        estimated_total_cost
                    ),
                    currency=currency,
                    factors=factors,
                    reason=(
                        "Supplier is available, but "
                        "component risk requires review "
                        "before procurement."
                    ),
                )

        if lifecycle is not None:
            if lifecycle.risk.value in {
                "HIGH",
                "CRITICAL",
            }:
                return ComponentDecision(
                    mpn=mpn,
                    manufacturer=manufacturer,
                    action=DecisionAction.REVIEW,
                    supplier=selected_supplier,
                    supplier_score=(
                        selected_score.total_score
                    ),
                    risk_score=(
                        risk.score
                        if risk is not None
                        else None
                    ),
                    lifecycle_status=(
                        lifecycle.status.value
                    ),
                    availability=availability,
                    estimated_unit_price=unit_price,
                    estimated_total_cost=(
                        estimated_total_cost
                    ),
                    currency=currency,
                    factors=factors,
                    reason=(
                        "Component lifecycle risk "
                        "requires review before "
                        "procurement."
                    ),
                )

        return ComponentDecision(
            mpn=mpn,
            manufacturer=manufacturer,
            action=DecisionAction.BUY,
            supplier=selected_supplier,
            supplier_score=selected_score.total_score,
            risk_score=(
                risk.score
                if risk is not None
                else None
            ),
            lifecycle_status=(
                lifecycle.status.value
                if lifecycle is not None
                else None
            ),
            availability=availability,
            estimated_unit_price=unit_price,
            estimated_total_cost=estimated_total_cost,
            currency=currency,
            factors=factors,
            reason=(
                recommendation.reason
            ),
        )