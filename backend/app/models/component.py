from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.bom_component import BOMComponent
    from backend.app.models.lifecycle import LifecycleRecord
    from backend.app.models.risk import RiskRecord


class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # ------------------------------------------------------------------
    # Core component identity
    # ------------------------------------------------------------------

    mpn: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )

    manufacturer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Existing component metadata
    # ------------------------------------------------------------------

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    category: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    package: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Phase 5A: Normalized component identity
    # ------------------------------------------------------------------

    normalized_mpn: Mapped[str | None] = mapped_column(
        String(150),
        index=True,
        nullable=True,
    )

    normalized_manufacturer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    normalized_category: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Phase 5A: External component references
    # ------------------------------------------------------------------

    datasheet_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    manufacturer_part_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Phase 5A: Enrichment state
    # ------------------------------------------------------------------

    enrichment_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )

    enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    boms: Mapped[list["BOMComponent"]] = relationship(
        back_populates="component",
        passive_deletes="all",
    )

    lifecycle_records: Mapped[list["LifecycleRecord"]] = relationship(
        back_populates="component",
        cascade="all, delete-orphan",
    )

    risk_records: Mapped[list["RiskRecord"]] = relationship(
        back_populates="component",
        cascade="all, delete-orphan",
    )