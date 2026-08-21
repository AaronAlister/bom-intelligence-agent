from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class DocumentIngestionRecord(Base):
    """
    Persistent record describing an engineering document ingestion run.
    """

    __tablename__ = "document_ingestion_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    document_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    source_file: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    source_format: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    pages_processed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    chunks_created: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    chunks_indexed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )