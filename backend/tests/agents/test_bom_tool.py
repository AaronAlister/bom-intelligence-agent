from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.agents.tools.bom import (
    BOMIntelligenceTool,
)


@pytest.mark.asyncio
async def test_bom_tool_delegates_to_service():
    service = AsyncMock()

    result_model = MagicMock()
    result_model.model_dump.return_value = {
        "components": [],
        "cost": {},
        "risk": {},
    }

    service.analyze.return_value = result_model

    tool = BOMIntelligenceTool(service)

    result = await tool.execute(
        bom_id="BOM-001",
        component_ids=["1", "2"],
        context={
            "components": [
                {
                    "component_id": 1,
                    "mpn": "ABC123",
                    "manufacturer": "Acme",
                    "quantity": 2,
                },
                {
                    "component_id": 2,
                    "mpn": "XYZ456",
                    "manufacturer": "Beta",
                    "quantity": 4,
                },
            ]
        },
    )

    assert result.status == "success"
    assert result.tool_name == "bom_intelligence"

    assert len(result.evidence) == 1
    assert (
        result.evidence[0].source
        == "bom_intelligence"
    )
    assert (
        result.evidence[0].source_id
        == "BOM-001"
    )

    service.analyze.assert_awaited_once_with(
        components=[
            (1, "ABC123", "Acme", 2),
            (2, "XYZ456", "Beta", 4),
        ]
    )


@pytest.mark.asyncio
async def test_bom_tool_requires_components():
    service = AsyncMock()

    tool = BOMIntelligenceTool(service)

    result = await tool.execute(
        bom_id="BOM-001",
        component_ids=[],
        context={},
    )

    assert result.status == "failed"
    assert result.error is not None
    assert "component data" in result.error
    service.analyze.assert_not_awaited()