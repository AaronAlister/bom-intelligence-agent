from typing import Any

from backend.app.agents.contracts import Evidence
from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import (
    AgentTool,
    serialize_result,
)
from backend.app.intelligence.component.service import (
    ComponentIntelligenceService,
)


class ComponentIntelligenceTool(AgentTool):
    """
    Agent adapter for component intelligence.

    Delegates all component analysis to the existing
    ComponentIntelligenceService and emits deterministic
    evidence describing the source of the analysis.
    """

    name = "component_intelligence"

    description = (
        "Analyze component procurement, availability, "
        "lifecycle, risk, supplier quotes, and decision."
    )

    dependencies: tuple[str, ...] = ()

    def __init__(
        self,
        intelligence_service: ComponentIntelligenceService,
    ) -> None:
        self._intelligence_service = intelligence_service

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        components = context.get("components", [])

        if not components:
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error=(
                    "Component intelligence requires "
                    "component data in context."
                ),
            )

        results = []

        try:
            for component in components:
                result = await self._intelligence_service.analyze(
                    mpn=component["mpn"],
                    manufacturer=component.get(
                        "manufacturer"
                    ),
                    quantity=component.get(
                        "quantity",
                        1,
                    ),
                )

                results.append(
                    {
                        "component_id": component[
                            "component_id"
                        ],
                        "result": serialize_result(
                            result
                        ),
                    }
                )

        except (KeyError, TypeError, ValueError) as exc:
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error=str(exc),
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error=(
                    "Component intelligence execution "
                    f"failed: {exc}"
                ),
            )

        evidence = [
            Evidence(
                source="component_intelligence",
                source_id=str(component["mpn"]),
                excerpt=(
                    "Component intelligence analysis "
                    f"completed for {component['mpn']}."
                ),
                metadata={
                    "bom_id": bom_id,
                    "component_id": component[
                        "component_id"
                    ],
                    "manufacturer": component.get(
                        "manufacturer"
                    ),
                    "quantity": component.get(
                        "quantity",
                        1,
                    ),
                },
            )
            for component in components
        ]

        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "bom_id": bom_id,
                "components": results,
            },
            evidence=evidence,
        )