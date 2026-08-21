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


@pytest.mark.asyncio
async def test_document_ingestion_repository_create_and_get():
    document_id = (
        f"DOC-REPO-TEST-{uuid.uuid4().hex[:8]}"
    )

    async with AsyncSessionLocal() as session:
        record = await DocumentIngestionRepository.create(
            session,
            document_id=document_id,
            source_file="test-datasheet.pdf",
            source_format="pdf",
            status="completed",
            pages_processed=3,
            chunks_created=3,
            chunks_indexed=3,
        )

        await session.commit()

        ingestion_id = record.id

    async with AsyncSessionLocal() as session:
        fetched = (
            await DocumentIngestionRepository.get_by_id(
                session,
                ingestion_id,
            )
        )

        assert fetched is not None
        assert fetched.document_id == document_id
        assert fetched.source_file == (
            "test-datasheet.pdf"
        )
        assert fetched.source_format == "pdf"
        assert fetched.status == "completed"
        assert fetched.pages_processed == 3
        assert fetched.chunks_created == 3
        assert fetched.chunks_indexed == 3
        assert fetched.error_message is None

        await session.execute(
            delete(
                DocumentIngestionRecord
            ).where(
                DocumentIngestionRecord.id
                == ingestion_id
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_document_ingestion_repository_lists_by_document():
    document_id = (
        f"DOC-REPO-LIST-{uuid.uuid4().hex[:8]}"
    )

    async with AsyncSessionLocal() as session:
        first = (
            await DocumentIngestionRepository.create(
                session,
                document_id=document_id,
                source_file="first.pdf",
                source_format="pdf",
                status="processing",
            )
        )

        second = (
            await DocumentIngestionRepository.create(
                session,
                document_id=document_id,
                source_file="second.pdf",
                source_format="pdf",
                status="completed",
                pages_processed=2,
                chunks_created=2,
                chunks_indexed=2,
            )
        )

        await session.commit()

        first_id = first.id
        second_id = second.id

    async with AsyncSessionLocal() as session:
        records = (
            await DocumentIngestionRepository.list_for_document(
                session,
                document_id,
            )
        )

        assert len(records) == 2

        assert records[0].id == first_id
        assert records[1].id == second_id

        await session.execute(
            delete(
                DocumentIngestionRecord
            ).where(
                DocumentIngestionRecord.id.in_(
                    [first_id, second_id]
                )
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_document_ingestion_repository_returns_none_for_unknown_id():
    async with AsyncSessionLocal() as session:
        result = (
            await DocumentIngestionRepository.get_by_id(
                session,
                999999999,
            )
        )

        assert result is None


@pytest.mark.asyncio
async def test_document_ingestion_repository_returns_empty_for_unknown_document():
    async with AsyncSessionLocal() as session:
        records = (
            await DocumentIngestionRepository.list_for_document(
                session,
                "DOC-DOES-NOT-EXIST",
            )
        )

        assert records == []