"""add user ownership foreign key

Revision ID: a6b0f1c2d3e4
Revises: 7fd904b9f5b1
Create Date: 2026-10-28

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a6b0f1c2d3e4"
down_revision: Union[str, None] = "7fd904b9f5b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_documents_uploaded_by_users",
        "documents",
        "users",
        ["uploaded_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_documents_uploaded_by_users", "documents", type_="foreignkey")