from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.bom import BOM


class BOMRiskRecord(Base):
    __tablename__ = "bom_risk_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    bom_id: Mapped[int] = mapped_column(
        ForeignKey("boms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    component_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    high_risk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    critical_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    lifecycle_risk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    availability_risk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    bom: Mapped["BOM"] = relationship(
        back_populates="risk_records",
    )