from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ingestion import IngestionRecord


class IngestionRepository:

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        ingestion_id: int,
    ) -> IngestionRecord | None:
        result = await session.execute(
            select(IngestionRecord).where(
                IngestionRecord.id == ingestion_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_bom(
        session: AsyncSession,
        bom_id: int,
    ) -> list[IngestionRecord]:
        result = await session.execute(
            select(IngestionRecord)
            .where(IngestionRecord.bom_id == bom_id)
            .order_by(IngestionRecord.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        bom_id: int,
        source_file: str,
        source_format: str,
        status: str,
        row_count: int,
        error_count: int,
    ) -> IngestionRecord:
        record = IngestionRecord(
            bom_id=bom_id,
            source_file=source_file,
            source_format=source_format,
            status=status,
            row_count=row_count,
            error_count=error_count,
        )

        session.add(record)
        await session.flush()

        return record