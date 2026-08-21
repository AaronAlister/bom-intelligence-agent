import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from backend.app.main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_readiness_returns_ready_when_dependencies_are_healthy():
    with patch(
        "backend.app.api.routes.check_readiness",
        new=AsyncMock(
            return_value={
                "status": "ready",
                "dependencies": {
                    "database": "healthy",
                    "redis": "healthy",
                    "qdrant": "healthy",
                },
            }
        ),
    ):
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/health/ready"
            )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"
    assert data["dependencies"] == {
        "database": "healthy",
        "redis": "healthy",
        "qdrant": "healthy",
    }


@pytest.mark.asyncio
async def test_readiness_returns_503_when_dependency_fails():
    with patch(
        "backend.app.api.routes.check_readiness",
        new=AsyncMock(
            return_value={
                "status": "not_ready",
                "dependencies": {
                    "database": "healthy",
                    "redis": "unhealthy",
                    "qdrant": "healthy",
                },
            }
        ),
    ):
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/health/ready"
            )

    assert response.status_code == 503

    data = response.json()

    assert data["detail"]["status"] == "not_ready"
    assert (
        data["detail"]["dependencies"]["redis"]
        == "unhealthy"
    )