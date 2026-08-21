from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from backend.app.api import document_routes
from backend.app.api.document_dependencies import (
    get_document_ingestion_service,
)
from backend.app.api.document_routes import (
    router,
)
from backend.app.rag.documents.service import (
    DocumentIngestionService,
)


class FakeDocumentIngestionService:
    """
    Deterministic ingestion service for API tests.
    """

    def __init__(self) -> None:
        self.received_files: list[bytes] = []

    async def ingest(
        self,
        *,
        file_path: Path,
    ) -> dict[str, int | str]:
        self.received_files.append(
            file_path.read_bytes()
        )

        return {
            "document_id": "DOC-API-001",
            "source": file_path.name,
            "pages_processed": 3,
            "chunks_created": 5,
            "chunks_indexed": 5,
        }


def create_test_app(
    service: FakeDocumentIngestionService,
) -> FastAPI:
    """
    Create a minimal FastAPI application containing
    only the document API router.
    """

    app = FastAPI()

    app.include_router(
        router,
        prefix="/api/v1",
    )

    def override_service() -> (
        FakeDocumentIngestionService
    ):
        return service

    app.dependency_overrides[
        get_document_ingestion_service
    ] = override_service

    return app


def test_upload_document_success() -> None:
    service = FakeDocumentIngestionService()

    app = create_test_app(service)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "datasheet.pdf",
                    b"%PDF-test-content",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    assert response.json() == {
        "document_id": "DOC-API-001",
        "source": "datasheet.pdf",
        "pages_processed": 3,
        "chunks_created": 5,
        "chunks_indexed": 5,
    }

    assert service.received_files == [
        b"%PDF-test-content"
    ]


def test_upload_document_rejects_unsupported_format() -> None:
    service = FakeDocumentIngestionService()

    app = create_test_app(service)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "datasheet.txt",
                    b"engineering data",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Unsupported document format: .txt. "
        "Currently supported formats are: .pdf"
    )

    assert service.received_files == []


def test_upload_document_rejects_empty_file() -> None:
    service = FakeDocumentIngestionService()

    app = create_test_app(service)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "empty.pdf",
                    b"",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 422

    assert response.json()["detail"] == (
        "The uploaded document file is empty."
    )

    assert service.received_files == []


def test_upload_document_rejects_oversized_file(
    monkeypatch: MonkeyPatch,
) -> None:
    service = FakeDocumentIngestionService()

    app = create_test_app(service)

    monkeypatch.setattr(
        document_routes,
        "MAX_DOCUMENT_FILE_SIZE_BYTES",
        10,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "large.pdf",
                    b"01234567890",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 413

    assert response.json()["detail"] == (
        "Document file exceeds the maximum allowed "
        "size of 25 MB."
    )

    assert service.received_files == []


def test_upload_document_maps_ingestion_value_error(
    monkeypatch,
) -> None:
    class FailingService:
        async def ingest(
            self,
            *,
            file_path: Path,
        ) -> dict[str, int | str]:
            raise ValueError(
                "No searchable content found in document."
            )

    service = FailingService()

    app = FastAPI()

    app.include_router(
        router,
        prefix="/api/v1",
    )

    def override_service() -> FailingService:
        return service

    app.dependency_overrides[
        get_document_ingestion_service
    ] = override_service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "empty-content.pdf",
                    b"not-empty",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 422

    assert response.json()["detail"] == (
        "No searchable content found in document."
    )


def test_upload_document_maps_unexpected_failure() -> None:
    class FailingService:
        async def ingest(
            self,
            *,
            file_path: Path,
        ) -> dict[str, int | str]:
            raise RuntimeError(
                "Unexpected indexing failure."
            )

    service = FailingService()

    app = FastAPI()

    app.include_router(
        router,
        prefix="/api/v1",
    )

    def override_service() -> FailingService:
        return service

    app.dependency_overrides[
        get_document_ingestion_service
    ] = override_service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "datasheet.pdf",
                    b"valid-enough-content",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 500

    assert response.json()["detail"] == (
        "Document ingestion failed."
    )


def test_upload_document_rejects_missing_file() -> None:
    service = FakeDocumentIngestionService()

    app = create_test_app(service)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents/upload"
        )

    assert response.status_code == 422

    assert service.received_files == []