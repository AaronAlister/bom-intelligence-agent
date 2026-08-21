from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.agents.tools.component import (
    ComponentIntelligenceTool,
)


@pytest.mark.asyncio
async def test_component_tool_delegates_to_service():
    service = AsyncMock()

    result_model = MagicMock()
    result_model.model_dump.return_value = {
        "mpn": "ABC123",
        "risk": {
            "score": 0.2,
        },
    }

    service.analyze.return_value = result_model

    tool = ComponentIntelligenceTool(service)

    result = await tool.execute(
        bom_id="BOM-001",
        component_ids=["1"],
        context={
            "components": [
                {
                    "component_id": 1,
                    "mpn": "ABC123",
                    "manufacturer": "Acme",
                    "quantity": 2,
                }
            ]
        },
    )

    assert result.status == "success"
    assert result.tool_name == "component_intelligence"

    assert len(result.evidence) == 1
    assert (
        result.evidence[0].source
        == "component_intelligence"
    )
    assert (
        result.evidence[0].source_id
        == "ABC123"
    )
    assert (
        result.evidence[0].metadata["component_id"]
        == 1
    )

    service.analyze.assert_awaited_once_with(
        mpn="ABC123",
        manufacturer="Acme",
        quantity=2,
    )


@pytest.mark.asyncio
async def test_component_tool_requires_components():
    service = AsyncMock()

    tool = ComponentIntelligenceTool(service)

    result = await tool.execute(
        bom_id="BOM-001",
        component_ids=[],
        context={},
    )

    assert result.status == "failed"
    assert result.error is not None
    assert "component data" in result.error

    service.analyze.assert_not_awaited()