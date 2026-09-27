"""add formula region bounds

Revision ID: 7fd904b9f5b1
Revises: 1c603257d451
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7fd904b9f5b1"
down_revision: Union[str, None] = "1c603257d451"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("formula_entries", sa.Column("x_min", sa.Integer(), nullable=True))
    op.add_column("formula_entries", sa.Column("y_min", sa.Integer(), nullable=True))
    op.add_column("formula_entries", sa.Column("x_max", sa.Integer(), nullable=True))
    op.add_column("formula_entries", sa.Column("y_max", sa.Integer(), nullable=True))
    op.add_column("formula_entries", sa.Column("confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("formula_entries", "confidence")
    op.drop_column("formula_entries", "y_max")
    op.drop_column("formula_entries", "x_max")
    op.drop_column("formula_entries", "y_min")
    op.drop_column("formula_entries", "x_min")