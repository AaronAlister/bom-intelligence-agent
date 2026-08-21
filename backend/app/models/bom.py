from datetime import datetime
from typing import TYPE_CHECKING
from backend.app.models.bom_risk import BOMRiskRecord

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.bom_component import BOMComponent
    from backend.app.models.ingestion import IngestionRecord

class BOM(Base):
    __tablename__ = "boms"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    bom_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )

    product: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    revision: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_file: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    components: Mapped[list["BOMComponent"]] = relationship(
        back_populates="bom",
        cascade="all, delete-orphan",
    )

    ingestion_records: Mapped[list["IngestionRecord"]] = relationship(
        back_populates="bom",
        cascade="all, delete-orphan",
    )

    risk_records: Mapped[list["BOMRiskRecord"]] = relationship(
    back_populates="bom",
    cascade="all, delete-orphan",
    )