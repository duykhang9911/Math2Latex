import logging
from pathlib import Path
from uuid import UUID

import pymupdf

from app.core.database import SessionLocal
from app.models import Document, FormulaEntry
from app.services.formula_regions import detect_page_regions

logger = logging.getLogger(__name__)


def render_pdf_pages(pdf_path: Path, output_dir: Path, dpi: int = 150) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    scale = dpi / 72

    with pymupdf.open(pdf_path) as pdf:
        if pdf.is_encrypted and not pdf.authenticate(""):
            raise ValueError("PDF được bảo vệ bằng mật khẩu")
        if len(pdf) == 0:
            raise ValueError("PDF không có trang")

        for page_index, page in enumerate(pdf):
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            pixmap.save(output_dir / f"page-{page_index + 1:06d}.png")

        return len(pdf)


def process_pdf_pages(document_id: UUID, pdf_path: Path) -> None:
    db = SessionLocal()
    try:
        pages_dir = pdf_path.parent / "pages"
        render_pdf_pages(pdf_path, pages_dir)
        document = db.get(Document, document_id)
        if document is not None:
            document.status = "detecting_formulas"
            db.commit()

        formulas_dir = pdf_path.parent / "formulas"
        proposals = []
        for page_number, page_image in enumerate(sorted(pages_dir.glob("page-*.png")), start=1):
            proposals.extend(
                detect_page_regions(document_id, page_number, page_image, formulas_dir)
            )

        db.add_all([FormulaEntry(**proposal) for proposal in proposals])
        document = db.get(Document, document_id)
        if document is not None:
            document.status = "formula_proposals_ready"
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to process pages for document %s", document_id)
        formulas_dir = pdf_path.parent / "formulas"
        if formulas_dir.exists():
            for crop_path in formulas_dir.glob("*.png"):
                crop_path.unlink(missing_ok=True)
        document = db.get(Document, document_id)
        if document is not None:
            document.status = "processing_failed"
            db.commit()
    finally:
        db.close()