from backend.app.intelligence.availability.supplier.bom_cost import (
    BOMCostCalculator,
)
from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.component.service import (
    ComponentIntelligenceService,
)
from backend.app.intelligence.bom.models import (
    BOMComponentIntelligence,
    BOMIntelligenceResult,
)
from backend.app.intelligence.risk.bom_assessor import (
    BOMRiskAssessor,
)
from backend.app.intelligence.risk.bom_explainer import (
    BOMRiskExplainer,
)
from backend.app.intelligence.risk.bom_models import (
    BOMComponentRisk,
)


class BOMIntelligenceService:
    """
    Coordinates complete intelligence for an entire BOM.

    Pipeline:

        Component intelligence
                ↓
        Component risk extraction
                ↓
        BOM risk aggregation
                ↓
        BOM risk explanation

        Supplier quotes
                ↓
        BOM cost calculation
    """

    def __init__(
        self,
        component_service: ComponentIntelligenceService,
    ) -> None:
        self._component_service = component_service

    async def analyze(
        self,
        *,
        components: list[
            tuple[int, str, str | None, int]
        ],
    ) -> BOMIntelligenceResult:
        """
        Analyze every component in the BOM.

        Each component tuple contains:

            (
                component_id,
                mpn,
                manufacturer,
                quantity,
            )
        """

        if not components:
            raise ValueError(
                "At least one BOM component is required"
            )

        component_results: list[
            BOMComponentIntelligence
        ] = []

        cost_inputs: list[
            tuple[SupplierQuote, int]
        ] = []

        component_risks: list[
            BOMComponentRisk
        ] = []

        for (
            component_id,
            mpn,
            manufacturer,
            quantity,
        ) in components:

            if quantity <= 0:
                raise ValueError(
                    "Quantity must be greater than zero"
                )

            intelligence = (
                await self._component_service.analyze(
                    mpn=mpn,
                    manufacturer=manufacturer,
                    quantity=quantity,
                )
            )

            component_results.append(
                BOMComponentIntelligence(
                    component_id=component_id,
                    mpn=mpn,
                    quantity=quantity,
                    intelligence=intelligence,
                )
            )

            if intelligence.risk is None:
                raise RuntimeError(
                    "Component intelligence did not "
                    "produce a risk assessment"
                )

            lifecycle_risk = (
                intelligence.risk.lifecycle_score > 0
            )

            availability_risk = (
                intelligence.risk.availability_score > 0
            )

            component_risks.append(
                BOMComponentRisk(
                    component_id=component_id,
                    mpn=mpn,
                    quantity=quantity,
                    score=intelligence.risk.score,
                    severity=intelligence.risk.severity,
                    lifecycle_risk=lifecycle_risk,
                    availability_risk=availability_risk,
                )
            )

            decision = intelligence.decision

            if (
                decision is not None
                and decision.supplier is not None
                and decision.estimated_unit_price
                is not None
            ):
                quote = SupplierQuote(
                    supplier=decision.supplier,
                    manufacturer=manufacturer,
                    mpn=mpn,
                    unit_price=(
                        decision.estimated_unit_price
                    ),
                    currency=decision.currency,
                    quantity_available=(
                        decision.availability
                    ),
                    source="decision",
                )

                cost_inputs.append(
                    (
                        quote,
                        quantity,
                    )
                )

        risk = BOMRiskAssessor.assess(
            component_risks
        )

        risk_explanation = BOMRiskExplainer.explain(
            risk
        )

        if cost_inputs:
            cost = BOMCostCalculator(
                cost_inputs
            ).calculate()
        else:
            from backend.app.intelligence.availability.supplier.bom_cost import (
                BOMCost,
            )

            cost = BOMCost(
                components=[],
                total_cost=None,
                currency=None,
            )

        return BOMIntelligenceResult(
            components=component_results,
            cost=cost,
            risk=risk,
            risk_explanation=risk_explanation,
        )