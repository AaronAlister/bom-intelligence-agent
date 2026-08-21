from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.ingestion.schemas import (
    BOMMetadata,
    BOMComponent,
    IngestionResult,
)
from backend.app.services.bom_ingestion_service import (
    BOMIngestionService,
)


def make_valid_result() -> IngestionResult:
    return IngestionResult(
        bom_id="test-bom-id",
        bom_database_id=None,  # Added: will be set after persistence
        source_file="test.csv",
        source_format="csv",
        metadata=BOMMetadata(
            bom_id="test-bom-id",
            bom_database_id=None,  # Added: will be set after persistence
            product="Test Board",
            revision="A",
            source_file="test.csv",
            source_format="csv",
            ingested_at=datetime(
                2026,
                8,
                12,
                tzinfo=timezone.utc,
            ),
        ),
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        components=[
            BOMComponent(
                mpn="LM358DR",
                manufacturer="Texas Instruments",
                description="Dual operational amplifier",
                quantity=2,
                reference_designators=[
                    "U1",
                    "U2",
                ],
            )
        ],
        validation_issues=[],
    )


def make_invalid_result() -> IngestionResult:
    return IngestionResult(
        bom_id="invalid-bom-id",
        bom_database_id=None,  # Added
        source_file="invalid.csv",
        source_format="csv",
        metadata=BOMMetadata(
            bom_id="invalid-bom-id",
            bom_database_id=None,  # Added
            product=None,
            revision=None,
            source_file="invalid.csv",
            source_format="csv",
            ingested_at=datetime(
                2026,
                8,
                12,
                tzinfo=timezone.utc,
            ),
        ),
        total_rows=1,
        valid_rows=0,
        invalid_rows=1,
        components=[],
        validation_issues=[],
    )


@pytest.mark.asyncio
async def test_valid_bom_is_persisted():

    session = AsyncMock()

    result = make_valid_result()

    with patch(
        "backend.app.services.bom_ingestion_service.ingest_bom",
        return_value=result,
    ) as mock_ingest, patch(
        "backend.app.services.bom_ingestion_service."
        "BOMPersistenceService.persist_bom",
        new_callable=AsyncMock,
        return_value=(
            type("PersistedBOM", (), {"id": 1})(),
            type("IngestionRecord", (), {})(),
        ),
    ) as mock_persist:

        returned = (
            await BOMIngestionService.ingest_and_persist(
                session=session,
                file_path=Path("test.csv"),
            )
        )

    assert returned == result

    mock_ingest.assert_called_once()

    mock_persist.assert_awaited_once()

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_bom_is_not_persisted():

    session = AsyncMock()

    result = make_invalid_result()

    with patch(
        "backend.app.services.bom_ingestion_service.ingest_bom",
        return_value=result,
    ) as mock_ingest, patch(
        "backend.app.services.bom_ingestion_service."
        "BOMPersistenceService.persist_bom",
        new_callable=AsyncMock,
        return_value=(
            type("PersistedBOM", (), {"id": 1})(),
            type("IngestionRecord", (), {})(),
        ),
    ) as mock_persist:

        returned = (
            await BOMIngestionService.ingest_and_persist(
                session=session,
                file_path=Path("invalid.csv"),
            )
        )

    assert returned == result

    mock_ingest.assert_called_once()

    mock_persist.assert_not_awaited()

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_bom_is_not_persisted():

    session = AsyncMock()

    result = IngestionResult(
        bom_id="empty-bom-id",
        bom_database_id=None,  # Added
        source_file="empty.csv",
        source_format="csv",
        metadata=BOMMetadata(
            bom_id="empty-bom-id",
            bom_database_id=None,  # Added
            product=None,
            revision=None,
            source_file="empty.csv",
            source_format="csv",
            ingested_at=datetime(
                2026,
                8,
                12,
                tzinfo=timezone.utc,
            ),
        ),
        total_rows=0,
        valid_rows=0,
        invalid_rows=0,
        components=[],
        validation_issues=[],
    )

    with patch(
        "backend.app.services.bom_ingestion_service.ingest_bom",
        return_value=result,
    ) as mock_ingest, patch(
        "backend.app.services.bom_ingestion_service."
        "BOMPersistenceService.persist_bom",
        new_callable=AsyncMock,
        return_value=(
            type("PersistedBOM", (), {"id": 1})(),
            type("IngestionRecord", (), {})(),
        ),
    ) as mock_persist:

        returned = (
            await BOMIngestionService.ingest_and_persist(
                session=session,
                file_path=Path("empty.csv"),
            )
        )

    assert returned == result

    mock_ingest.assert_called_once()

    mock_persist.assert_not_awaited()

    session.commit.assert_not_awaited()