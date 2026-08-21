from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.agents.tools.alternative import (
    AlternativeTool,
)


@pytest.mark.asyncio
async def test_alternative_tool_requires_component_data():
    session = AsyncMock()

    tool = AlternativeTool(session)

    result = await tool.execute(
        bom_id="BOM-001",
        component_ids=["1"],
        context={},
    )

    assert result.status == "failed"
    assert result.error is not None
    assert "source component data" in result.error


@pytest.mark.asyncio
async def test_alternative_tool_calls_service():
    session = AsyncMock()

    analysis = MagicMock()
    analysis.model_dump.return_value = {
        "source_mpn": "ABC123",
        "candidates": [],
        "best_candidate": None,
    }

    with patch(
        "backend.app.agents.tools.alternative."
        "AlternativeComponentService.find_alternatives",
        new_callable=AsyncMock,
        return_value=analysis,
    ) as find_alternatives:

        tool = AlternativeTool(session)

        result = await tool.execute(
            bom_id="BOM-001",
            component_ids=["1"],
            context={
                "alternative_components": [
                    {
                        "component_id": 1,
                        "mpn": "ABC123",
                        "manufacturer": "Acme",
                        "description": "Test component",
                        "category": "IC",
                        "package": "QFN",
                    }
                ]
            },
        )

    assert result.status == "success"
    assert result.tool_name == "alternative_analysis"
    assert len(result.evidence) == 1
    assert (
        result.evidence[0].source
        == "alternative_analysis"
    )
    assert (
        result.evidence[0].source_id
        == "1"
    )
    find_alternatives.assert_awaited_once()