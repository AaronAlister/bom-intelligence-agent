from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories.document_ingestion_repository import (
    DocumentIngestionRepository,
)


class DocumentIngestionPersistence:
    """
    PostgreSQL persistence adapter for document ingestion.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def record_success(
        self,
        *,
        document_id: str,
        source_file: str,
        source_format: str,
        pages_processed: int,
        chunks_created: int,
        chunks_indexed: int,
    ) -> None:
        await DocumentIngestionRepository.create(
            self._session,
            document_id=document_id,
            source_file=source_file,
            source_format=source_format,
            status="completed",
            pages_processed=pages_processed,
            chunks_created=chunks_created,
            chunks_indexed=chunks_indexed,
        )

        await self._session.commit()