import uuid

import fitz
import pytest
from httpx import ASGITransport, AsyncClient
from qdrant_client import QdrantClient
from sqlalchemy import delete

from backend.app.core.config import settings
from backend.app.db.repositories import (
    DocumentIngestionRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.document_ingestion import (
    DocumentIngestionRecord,
)
from backend.app.rag.vector_store import (
    QdrantVectorStore,
)


BASE_URL = "http://test"


def create_test_pdf() -> bytes:
    document = fitz.open()

    try:
        page = document.new_page()

        page.insert_text(
            (72, 72),
            "ACME-REG-001 Datasheet\n"
            "Input voltage range: 4.5 V to 5.5 V.\n"
            "Maximum output current: 300 mA.",
        )

        return document.tobytes()

    finally:
        document.close()


@pytest.mark.asyncio
async def test_document_upload_persists_ingestion_record():
    unique_name = (
        f"ACME-{uuid.uuid4().hex[:8]}_datasheet.pdf"
    )

    qdrant_client = QdrantClient(
        location=":memory:",
    )

    vector_store = QdrantVectorStore(
        qdrant_client,
        collection_name=(
            f"test_document_persistence_"
            f"{uuid.uuid4().hex[:8]}"
        ),
        vector_size=settings.embedding_dimension,
    )

    vector_store.ensure_collection()

    previous_vector_store = getattr(
        app.state,
        "rag_vector_store",
        None,
    )

    app.state.rag_vector_store = vector_store

    try:
        transport = ASGITransport(
            app=app,
        )

        async with AsyncClient(
            transport=transport,
            base_url=BASE_URL,
        ) as client:
            response = await client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        unique_name,
                        create_test_pdf(),
                        "application/pdf",
                    )
                },
            )

        assert response.status_code == 200

        data = response.json()

        document_id = data["document_id"]

        assert data["source"] == unique_name
        assert data["pages_processed"] == 1
        assert data["chunks_created"] >= 1
        assert data["chunks_indexed"] >= 1

        async with AsyncSessionLocal() as session:
            records = (
                await DocumentIngestionRepository.list_for_document(
                    session,
                    document_id,
                )
            )

            assert len(records) == 1

            record = records[0]

            assert record.document_id == document_id
            assert record.source_file == unique_name
            assert record.source_format == "pdf"
            assert record.status == "completed"
            assert record.pages_processed == 1
            assert record.chunks_created == data[
                "chunks_created"
            ]
            assert record.chunks_indexed == data[
                "chunks_indexed"
            ]

            await session.execute(
                delete(
                    DocumentIngestionRecord
                ).where(
                    DocumentIngestionRecord.id
                    == record.id
                )
            )

            await session.commit()

    finally:
        if previous_vector_store is None:
            try:
                del app.state.rag_vector_store
            except AttributeError:
                pass
        else:
            app.state.rag_vector_store = (
                previous_vector_store
            )

        qdrant_client.close()