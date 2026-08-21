import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


BASE_URL = "http://test"


@pytest.mark.asyncio
async def test_component_intelligence_unknown_component_returns_404():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/components/999999999/intelligence"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Component 999999999 not found."
    )


@pytest.mark.asyncio
async def test_component_intelligence_invalid_quantity_returns_422():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/components/1/intelligence",
            params={"quantity": 0},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bom_intelligence_unknown_bom_returns_404():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/999999999/intelligence"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "BOM 999999999 not found."
    )


@pytest.mark.asyncio
async def test_bom_risk_unknown_bom_returns_404():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.get(
            "/api/v1/boms/999999999/risk"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "BOM 999999999 not found."
    )


@pytest.mark.asyncio
async def test_bom_risk_history_unknown_bom_returns_404():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.get(
            "/api/v1/boms/999999999/risk/history"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "BOM 999999999 not found."
    )


@pytest.mark.asyncio
async def test_alternatives_unknown_component_returns_404():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.get(
            "/api/v1/components/999999999/alternatives"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Component 999999999 not found."
    )


@pytest.mark.asyncio
async def test_alternatives_invalid_limit_returns_422():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.get(
            "/api/v1/components/1/alternatives",
            params={"limit": 0},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_alternatives_limit_above_maximum_returns_422():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.get(
            "/api/v1/components/1/alternatives",
            params={"limit": 51},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_component_intelligence_invalid_path_type_returns_422():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/components/not-an-id/intelligence"
        )

    assert response.status_code == 422


# FIXED: renamed and changed assertion to 404
@pytest.mark.asyncio
async def test_bom_intelligence_unknown_bom_id_returns_404():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/not-an-id/intelligence"
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bom_agent_unknown_bom_returns_404():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/999999999/agent",
            json={
                "bom_id": "ignored",
                "task": "Analyze this BOM",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "BOM 999999999 not found."
    )


@pytest.mark.asyncio
async def test_bom_agent_invalid_path_type_returns_422():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/not-an-id/agent",
            json={
                "bom_id": "ignored",
                "task": "Analyze this BOM",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bom_agent_missing_request_body_returns_422():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/999999999/agent"
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bom_agent_missing_task_returns_422():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/999999999/agent",
            json={
                "bom_id": "999999999",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bom_agent_invalid_request_types_returns_422():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        response = await client.post(
            "/api/v1/boms/999999999/agent",
            json={
                "bom_id": 999999999,
                "task": 123,
                "component_ids": "not-a-list",
            },
        )

    assert response.status_code == 422


def test_openapi_contains_document_upload_endpoint():
    client = TestClient(app)

    response = client.get(
        "/api/openapi.json"
    )

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/documents/upload" in paths

    operation = paths[
        "/api/v1/documents/upload"
    ]["post"]

    assert operation["tags"] == [
        "Documents"
    ]


def test_openapi_document_upload_request_contract():
    client = TestClient(app)

    response = client.get(
        "/api/openapi.json"
    )

    assert response.status_code == 200

    operation = response.json()["paths"][
        "/api/v1/documents/upload"
    ]["post"]

    request_body = operation[
        "requestBody"
    ]

    assert request_body["required"] is True

    content = request_body["content"]

    assert "multipart/form-data" in content

    schema = content[
        "multipart/form-data"
    ]["schema"]

    assert schema == {
        "$ref": (
            "#/components/schemas/"
            "Body_upload_document_api_v1_documents_upload_post"
        )
    }


def test_openapi_document_upload_response_contract():
    client = TestClient(app)

    response = client.get(
        "/api/openapi.json"
    )

    assert response.status_code == 200

    operation = response.json()["paths"][
        "/api/v1/documents/upload"
    ]["post"]

    response_schema = operation[
        "responses"
    ]["200"]["content"][
        "application/json"
    ]["schema"]

    assert response_schema == {
        "$ref": (
            "#/components/schemas/"
            "DocumentIngestionResponse"
        )
    }


def test_openapi_document_ingestion_response_schema():
    client = TestClient(app)

    response = client.get(
        "/api/openapi.json"
    )

    assert response.status_code == 200

    schemas = response.json()[
        "components"
    ]["schemas"]

    schema = schemas[
        "DocumentIngestionResponse"
    ]

    assert schema["type"] == "object"

    properties = schema["properties"]

    assert properties[
        "document_id"
    ]["type"] == "string"

    assert properties[
        "source"
    ]["type"] == "string"

    assert properties[
        "pages_processed"
    ]["type"] == "integer"

    assert properties[
        "pages_processed"
    ]["minimum"] == 1

    assert properties[
        "chunks_created"
    ]["type"] == "integer"

    assert properties[
        "chunks_created"
    ]["minimum"] == 1

    assert properties[
        "chunks_indexed"
    ]["type"] == "integer"

    assert properties[
        "chunks_indexed"
    ]["minimum"] == 0