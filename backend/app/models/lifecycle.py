from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.component import Component


class LifecycleRecord(Base):
    __tablename__ = "lifecycle_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    component_id: Mapped[int] = mapped_column(
        ForeignKey("components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    eol_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    last_buy_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    component: Mapped["Component"] = relationship(
        back_populates="lifecycle_records",
    )