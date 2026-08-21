from fastapi.testclient import TestClient

from backend.app.main import app


def test_openapi_document_is_available():
    client = TestClient(app)

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    data = response.json()

    assert "openapi" in data
    assert "info" in data
    assert "paths" in data


def test_openapi_contains_intelligence_endpoints():
    client = TestClient(app)

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/components/{component_id}/intelligence" in paths
    assert "/api/v1/boms/{bom_id}/intelligence" in paths
    assert "/api/v1/boms/{bom_id}/agent" in paths


def test_openapi_contains_alternative_endpoints():
    client = TestClient(app)

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert (
        "/api/v1/components/{component_id}/alternatives"
        in paths
    )

    assert (
        "/api/v1/components/{component_id}/alternatives/analyze"
        in paths
    )

    assert (
        "/api/v1/components/{component_id}/alternatives/history"
        in paths
    )


def test_openapi_contains_health_endpoints():
    client = TestClient(app)

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/health" in paths
    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths


def test_openapi_contains_expected_tags():
    client = TestClient(app)

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    tags = {
        tag["name"]
        for tag in response.json().get("tags", [])
    }

    # Routes without explicit global metadata may not
    # appear here, so verify the operation-level tags.
    paths = response.json()["paths"]

    component_intelligence = paths[
        "/api/v1/components/{component_id}/intelligence"
    ]["post"]

    bom_intelligence = paths[
        "/api/v1/boms/{bom_id}/intelligence"
    ]["post"]

    alternatives = paths[
        "/api/v1/components/{component_id}/alternatives"
    ]["get"]

    assert "Component Intelligence" in (
        component_intelligence["tags"]
    )

    assert "BOM Intelligence" in (
        bom_intelligence["tags"]
    )

    assert "Components" in alternatives["tags"]


def test_openapi_agent_endpoint_contract():
    client = TestClient(app)

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    data = response.json()

    operation = data["paths"][
        "/api/v1/boms/{bom_id}/agent"
    ]["post"]

    assert operation["tags"] == ["BOM Agent"]

    assert operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {
        "$ref": "#/components/schemas/AgentResponse"
    }

    request_schema = operation[
        "requestBody"
    ]["content"]["application/json"]["schema"]

    assert request_schema == {
        "$ref": "#/components/schemas/AgentRequest"
    }


def test_openapi_agent_response_contains_evidence():
    client = TestClient(app)

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    schemas = response.json()["components"]["schemas"]

    agent_response = schemas["AgentResponse"]

    assert "evidence" in agent_response["properties"]

    assert agent_response["properties"]["evidence"] == {
        "items": {
            "$ref": "#/components/schemas/Evidence"
        },
        "type": "array",
        "title": "Evidence",
    }


def test_openapi_agent_response_contains_execution_metadata():
    client = TestClient(app)

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    schemas = response.json()["components"]["schemas"]

    agent_response = schemas["AgentResponse"]

    assert (
        "execution_metadata"
        in agent_response["properties"]
    )

    execution_metadata = (
        agent_response["properties"][
            "execution_metadata"
        ]
    )

    assert execution_metadata["type"] == "object"

    assert execution_metadata[
        "additionalProperties"
    ] is True
