from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document_ingestion import (
    DocumentIngestionRecord,
)


class DocumentIngestionRepository:
    """
    Repository for engineering document ingestion records.
    """

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        ingestion_id: int,
    ) -> DocumentIngestionRecord | None:
        result = await session.execute(
            select(DocumentIngestionRecord).where(
                DocumentIngestionRecord.id == ingestion_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_document(
        session: AsyncSession,
        document_id: str,
    ) -> list[DocumentIngestionRecord]:
        result = await session.execute(
            select(DocumentIngestionRecord)
            .where(
                DocumentIngestionRecord.document_id
                == document_id
            )
            .order_by(
                DocumentIngestionRecord.id
            )
        )

        return list(result.scalars().all())

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        document_id: str,
        source_file: str,
        source_format: str,
        status: str,
        pages_processed: int = 0,
        chunks_created: int = 0,
        chunks_indexed: int = 0,
        error_message: str | None = None,
    ) -> DocumentIngestionRecord:
        record = DocumentIngestionRecord(
            document_id=document_id,
            source_file=source_file,
            source_format=source_format,
            status=status,
            pages_processed=pages_processed,
            chunks_created=chunks_created,
            chunks_indexed=chunks_indexed,
            error_message=error_message,
        )

        session.add(record)
        await session.flush()

        return record