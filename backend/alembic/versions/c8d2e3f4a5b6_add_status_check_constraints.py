"""add status check constraints

Revision ID: c8d2e3f4a5b6
Revises: b7c1d2e3f4a5
Create Date: 2026-11-10

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c8d2e3f4a5b6"
down_revision: Union[str, None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Giá trị cố định tại thời điểm migration; không import từ app.models để revision này không đổi theo code.
DOCUMENT_STATUSES = (
    "uploaded",
    "processing_pages",
    "detecting_formulas",
    "formula_proposals_ready",
    "ocr_processing",
    "ocr_complete",
    "ocr_completed_with_errors",
    "processing_failed",
)
FORMULA_STATUSES = ("proposed", "ocr_queued", "ocr_complete", "ocr_failed", "submitted")


def _in_list(values: Sequence[str]) -> str:
    return "status IN (" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    op.create_check_constraint("ck_documents_status", "documents", _in_list(DOCUMENT_STATUSES))
    op.create_check_constraint("ck_formula_entries_status", "formula_entries", _in_list(FORMULA_STATUSES))


def downgrade() -> None:
    op.drop_constraint("ck_formula_entries_status", "formula_entries", type_="check")
    op.drop_constraint("ck_documents_status", "documents", type_="check")
