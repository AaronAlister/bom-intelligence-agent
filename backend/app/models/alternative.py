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
    from backend.app.models.component import Component


class AlternativeRecord(Base):
    """
    Historical alternative-component recommendation.
    """

    __tablename__ = "alternative_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    source_component_id: Mapped[int] = mapped_column(
        ForeignKey(
            "components.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    alternative_component_id: Mapped[int] = mapped_column(
        ForeignKey(
            "components.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    compatibility_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    category_match: Mapped[bool] = mapped_column(
        nullable=False,
    )

    package_match: Mapped[bool] = mapped_column(
        nullable=False,
    )

    manufacturer_match: Mapped[bool] = mapped_column(
        nullable=False,
    )

    lifecycle_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    availability_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    reasons: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source_component: Mapped["Component"] = relationship(
        foreign_keys=[source_component_id],
    )

    alternative_component: Mapped["Component"] = relationship(
        foreign_keys=[alternative_component_id],
    )