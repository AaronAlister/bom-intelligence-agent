from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.contracts import Evidence
from backend.app.agents.state import ToolResult
from backend.app.agents.tools.base import (
    AgentTool,
    serialize_result,
)
from backend.app.intelligence.component.service import (
    ComponentIntelligenceService,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.services.alternative_component import (
    AlternativeComponentService,
)


class AlternativeTool(AgentTool):
    """
    Agent adapter for alternative component discovery.

    This tool performs analysis only. It does not persist
    recommendations unless an explicit persistence action
    is introduced later.
    """

    name = "alternative_analysis"

    description = (
        "Find and rank compatible alternative components "
        "using compatibility, lifecycle, and availability."
    )

    dependencies: tuple[str, ...] = (
        "bom_intelligence",
    )

    def __init__(
        self,
        session: AsyncSession,
        intelligence_service: (
            ComponentIntelligenceService | None
        ) = None,
    ) -> None:
        self._session = session
        self._intelligence_service = intelligence_service

    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        if not component_ids:
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error=(
                    "Alternative analysis requires "
                    "at least one component ID."
                ),
            )

        source_components = context.get(
            "alternative_components",
            [],
        )

        if not source_components:
            return ToolResult(
                tool_name=self.name,
                status="failed",
                error=(
                    "Alternative analysis requires "
                    "source component data in context."
                ),
            )

        results = []

        try:
            for component in source_components:
                source_enrichment = (
                    ComponentEnrichmentResult(
                        mpn=component["mpn"],
                        manufacturer=component.get(
                            "manufacturer"
                        ),
                        description=component.get(
                            "description"
                        ),
                        category=component.get(
                            "category"
                        ),
                        package=component.get(
                            "package"
                        ),
                        lifecycle_status=None,
                        availability=None,
                        source="agent_context",
                    )
                )

                analysis = (
                    await AlternativeComponentService
                    .find_alternatives(
                        self._session,
                        component_id=component[
                            "component_id"
                        ],
                        source_enrichment=source_enrichment,
                        limit=component.get(
                            "limit",
                            10,
                        ),
                        intelligence_service=(
                            self._intelligence_service
                        ),
                    )
                )

                results.append(
                    {
                        "component_id": component[
                            "component_id"
                        ],
                        "analysis": serialize_result(
                            analysis
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
                    "Alternative analysis execution "
                    f"failed: {exc}"
                ),
            )

        evidence = [
            Evidence(
                source="alternative_analysis",
                source_id=str(component["component_id"]),
                excerpt=(
                    "Alternative component analysis "
                    f"completed for {component['mpn']}."
                ),
                metadata={
                    "bom_id": bom_id,
                    "component_id": component[
                        "component_id"
                    ],
                },
            )
            for component in source_components
        ]
        return ToolResult(
            tool_name=self.name,
            status="success",
            data={
                "bom_id": bom_id,
                "results": results,
            },
            evidence=evidence,
        )