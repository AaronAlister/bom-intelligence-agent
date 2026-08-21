from io import BytesIO

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)

def test_bom_upload_file_too_large(monkeypatch):

    import backend.app.api.bom_routes as bom_routes

    monkeypatch.setattr(
        bom_routes,
        "MAX_BOM_FILE_SIZE_BYTES",
        10,
    )

    response = client.post(
        "/api/v1/boms/upload",
        files={
            "file": (
                "large_bom.csv",
                BytesIO(
                    b"this file is definitely larger than 10 bytes"
                ),
                "text/csv",
            )
        },
    )

    assert response.status_code == 413

    data = response.json()

    assert "maximum allowed size" in data["detail"]

def test_bom_upload_unsupported_format():

    response = client.post(
        "/api/v1/boms/upload",
        files={
            "file": (
                "bom.txt",
                BytesIO(b"not a supported BOM"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert "Unsupported BOM format" in data["detail"]

def test_bom_upload_empty_file():

    response = client.post(
        "/api/v1/boms/upload",
        files={
            "file": (
                "empty.csv",
                BytesIO(b""),
                "text/csv",
            )
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert data["detail"] == (
        "The uploaded BOM file is empty."
    )

def test_bom_upload_missing_filename():

    response = client.post(
        "/api/v1/boms/upload",
        files={
            "file": (
                "",
                BytesIO(b"MPN,Quantity\nLM358DR,1"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 422

def test_bom_upload_success():

    response = client.post(
        "/api/v1/boms/upload",
        files={
            "file": (
                "valid_bom.csv",
                BytesIO(
                    (
                        "MPN,Manufacturer,Quantity\n"
                        "LM358DR,Texas Instruments,4\n"
                    ).encode("utf-8")
                ),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["source_file"] == "valid_bom.csv"

    assert data["source_format"] == "csv"

    assert data["total_rows"] == 1

    assert data["valid_rows"] == 1

    assert data["invalid_rows"] == 0

    assert len(data["components"]) == 1

    assert data["components"][0]["mpn"] == "LM358DR"

    assert data["components"][0]["quantity"] == 4

