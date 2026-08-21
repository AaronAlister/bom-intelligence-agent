"""create document ingestion records

Revision ID: create_doc_ingestion
Revises: f17c38ef036f
Create Date: 2026-08-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "create_doc_ingestion"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "0d471b3bcd82"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.create_table(
        "document_ingestion_records",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "source_file",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "source_format",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "pages_processed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "chunks_created",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "chunks_indexed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f(
            "ix_document_ingestion_records_document_id"
        ),
        "document_ingestion_records",
        ["document_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_document_ingestion_records_status"
        ),
        "document_ingestion_records",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f(
            "ix_document_ingestion_records_status"
        ),
        table_name="document_ingestion_records",
    )

    op.drop_index(
        op.f(
            "ix_document_ingestion_records_document_id"
        ),
        table_name="document_ingestion_records",
    )

    op.drop_table(
        "document_ingestion_records"
    )