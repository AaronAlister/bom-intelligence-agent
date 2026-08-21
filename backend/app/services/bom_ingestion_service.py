from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ingestion.pipeline import ingest_bom
from backend.app.ingestion.schemas import IngestionResult
from backend.app.services.bom_persistence import (
    BOMPersistenceService,
)


class BOMIngestionService:
    """
    Orchestrates BOM ingestion and database persistence.

    Responsibilities:
        1. Run the synchronous BOM ingestion pipeline.
        2. Reject invalid BOMs before persistence.
        3. Persist valid BOM data through the
           BOMPersistenceService.
        4. Attach the database BOM ID to the
           ingestion result.
        5. Return the completed IngestionResult.
    """

    @staticmethod
    async def ingest_and_persist(
        session: AsyncSession,
        file_path: Path,
        product: str | None = None,
        revision: str | None = None,
    ) -> IngestionResult:

        result = ingest_bom(
            file_path=file_path,
            product=product,
            revision=revision,
        )

        # Reject empty or fully invalid BOMs
        if result.total_rows == 0:
            return result

        if result.invalid_rows > 0:
            return result

        # Persist the valid BOM
        persisted_bom, _ = await BOMPersistenceService.persist_bom(
            session,
            bom_id=result.bom_id,
            product=result.metadata.product,
            revision=result.metadata.revision,
            source_file=result.source_file,
            source_format=result.source_format,
            components=[
                component.model_dump()
                for component in result.components
            ],
        )

        # Attach the database ID to both the result and its metadata
        result.bom_database_id = persisted_bom.id
        result.metadata.bom_database_id = persisted_bom.id

        await session.commit()

        return result