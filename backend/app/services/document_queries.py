from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import Document, FormulaEntry

# Đang có job worker ghi vào thư mục tài liệu; không cho xóa trong lúc này.
BUSY_STATUSES = {"processing_pages", "detecting_formulas", "ocr_processing"}


def summary_query(db: Session):
    """Document kèm số công thức và số công thức đã Submit (tính bằng aggregate, không lưu cột)."""
    counts = (
        db.query(
            FormulaEntry.document_id.label("document_id"),
            func.count(FormulaEntry.id).label("formula_count"),
            func.count(case((FormulaEntry.status == "submitted", 1))).label("submitted_count"),
        )
        .group_by(FormulaEntry.document_id)
        .subquery()
    )
    return db.query(
        Document,
        func.coalesce(counts.c.formula_count, 0),
        func.coalesce(counts.c.submitted_count, 0),
    ).outerjoin(counts, counts.c.document_id == Document.id)


def summary(document: Document, formula_count: int, submitted_count: int) -> dict:
    return {
        "document_id": document.id,
        "filename": document.filename,
        "status": document.status,
        "file_size_bytes": document.file_size_bytes,
        "page_count": document.page_count,
        "formula_count": formula_count,
        "submitted_count": submitted_count,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }
