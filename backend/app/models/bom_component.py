from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.bom import BOM
    from backend.app.models.component import Component


class BOMComponent(Base):
    __tablename__ = "bom_components"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    bom_id: Mapped[int] = mapped_column(
        ForeignKey("boms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    component_id: Mapped[int] = mapped_column(
        ForeignKey("components.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reference_designators: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "bom_id",
            "component_id",
            name="uq_bom_component",
        ),
    )

    bom: Mapped["BOM"] = relationship(
        back_populates="components",
    )

    component: Mapped["Component"] = relationship(
        back_populates="boms",
    )