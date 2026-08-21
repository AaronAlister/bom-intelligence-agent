from typing import Any

from backend.app.agents.contracts import Evidence
from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import (
    AgentTool,
    serialize_result,
)
from backend.app.intelligence.bom.service import (
    BOMIntelligenceService,
)


class BOMIntelligenceTool(AgentTool):
    """
    Agent adapter for complete BOM intelligence.

    Delegates BOM analysis to the existing
    BOMIntelligenceService.
    """

    name = "bom_intelligence"

    description = (
        "Analyze the complete BOM including component "
        "intelligence, risk, explanation, and cost."
    )

    dependencies: tuple[str, ...] = ()

    def __init__(
        self,
        intelligence_service: BOMIntelligenceService,
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
                    "BOM intelligence requires "
                    "component data in context."
                ),
            )

        try:
            component_inputs = [
                (
                    component["component_id"],
                    component["mpn"],
                    component.get("manufacturer"),
                    component.get("quantity", 1),
                )
                for component in components
            ]

            result = await self._intelligence_service.analyze(
                components=component_inputs,
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
                    "BOM intelligence execution "
                    f"failed: {exc}"
                ),
            )

        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "bom_id": bom_id,
                "result": serialize_result(result),
            },
            evidence=[
                Evidence(
                    source="bom_intelligence",
                    source_id=bom_id,
                    excerpt=(
                        "Complete BOM intelligence analysis "
                        f"completed for BOM {bom_id}."
                    ),
                    metadata={
                        "component_count": len(components),
                    },
                )
            ],
        )