"""add component enrichment fields

Revision ID: 6ffd421d6fbf
Revises: e8f9babe0cf7
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6ffd421d6fbf"
down_revision: Union[str, Sequence[str], None] = "e8f9babe0cf7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 5A component enrichment fields."""

    op.add_column(
        "components",
        sa.Column(
            "normalized_mpn",
            sa.String(length=150),
            nullable=True,
        ),
    )

    op.add_column(
        "components",
        sa.Column(
            "normalized_manufacturer",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "components",
        sa.Column(
            "normalized_category",
            sa.String(length=150),
            nullable=True,
        ),
    )

    op.add_column(
        "components",
        sa.Column(
            "datasheet_url",
            sa.String(length=1000),
            nullable=True,
        ),
    )

    op.add_column(
        "components",
        sa.Column(
            "manufacturer_part_url",
            sa.String(length=1000),
            nullable=True,
        ),
    )

    op.add_column(
        "components",
        sa.Column(
            "enrichment_status",
            sa.String(length=50),
            nullable=False,
            server_default="PENDING",
        ),
    )

    op.add_column(
        "components",
        sa.Column(
            "enriched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_components_normalized_mpn",
        "components",
        ["normalized_mpn"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Phase 5A component enrichment fields."""

    op.drop_index(
        "ix_components_normalized_mpn",
        table_name="components",
    )

    op.drop_column("components", "enriched_at")
    op.drop_column("components", "enrichment_status")
    op.drop_column("components", "manufacturer_part_url")
    op.drop_column("components", "datasheet_url")
    op.drop_column("components", "normalized_category")
    op.drop_column("components", "normalized_manufacturer")
    op.drop_column("components", "normalized_mpn")