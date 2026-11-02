"""add document history columns and log user

Revision ID: b7c1d2e3f4a5
Revises: a6b0f1c2d3e4
Create Date: 2026-11-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b7c1d2e3f4a5"
down_revision: Union[str, None] = "a6b0f1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE documents SET updated_at = created_at")
    op.create_index(
        "ix_documents_uploaded_by_created_at",
        "documents",
        ["uploaded_by", sa.text("created_at DESC")],
    )

    op.add_column("logs", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_logs_user_id_users",
        "logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_logs_user_id_users", "logs", type_="foreignkey")
    op.drop_column("logs", "user_id")
    op.drop_index("ix_documents_uploaded_by_created_at", table_name="documents")
    op.drop_column("documents", "updated_at")
    op.drop_column("documents", "page_count")
    op.drop_column("documents", "file_size_bytes")
