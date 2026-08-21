import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    DocumentIngestionRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.document_ingestion import (
    DocumentIngestionRecord,
)
from backend.app.rag.documents.persistence import (
    DocumentIngestionPersistence,
)


@pytest.mark.asyncio
async def test_document_ingestion_persistence_writes_to_postgresql():
    document_id = (
        f"DOC-PERSIST-{uuid.uuid4().hex[:8]}"
    )

    async with AsyncSessionLocal() as session:
        persistence = DocumentIngestionPersistence(
            session
        )

        await persistence.record_success(
            document_id=document_id,
            source_file="integration-test.pdf",
            source_format="pdf",
            pages_processed=3,
            chunks_created=3,
            chunks_indexed=3,
        )

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
        assert record.source_file == (
            "integration-test.pdf"
        )
        assert record.source_format == "pdf"
        assert record.status == "completed"
        assert record.pages_processed == 3
        assert record.chunks_created == 3
        assert record.chunks_indexed == 3

        await session.execute(
            delete(
                DocumentIngestionRecord
            ).where(
                DocumentIngestionRecord.id
                == record.id
            )
        )

        await session.commit()