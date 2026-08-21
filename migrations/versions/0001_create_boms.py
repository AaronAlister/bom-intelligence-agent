from alembic import op
import sqlalchemy as sa

revision = "0001_create_boms"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "boms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bom_id", sa.String(length=100), nullable=False),
        sa.Column("product", sa.String(length=255), nullable=True),
        sa.Column("revision", sa.String(length=100), nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_boms_bom_id", "boms", ["bom_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_boms_bom_id", table_name="boms")
    op.drop_table("boms")
