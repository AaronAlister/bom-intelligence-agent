from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.bom import BOM


class IngestionRecord(Base):
    __tablename__ = "ingestion_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    bom_id: Mapped[int] = mapped_column(
        ForeignKey("boms.id", ondelete="CASCADE"),
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
    )

    row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    bom: Mapped["BOM"] = relationship(
        back_populates="ingestion_records",
    )