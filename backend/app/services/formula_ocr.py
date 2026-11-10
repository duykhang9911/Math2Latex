import logging
from argparse import Namespace
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from PIL import Image

from app.core.database import SessionLocal
from app.models import Document, FormulaEntry

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_ocr_model():
    import torch
    from pix2tex.cli import LatexOCR

    arguments = Namespace(
        config="settings/config.yaml",
        checkpoint="checkpoints/weights.pth",
        no_cuda=not torch.cuda.is_available(),
        no_resize=False,
    )
    return LatexOCR(arguments)


def _fail_queued_formulas(db, document_id: UUID) -> None:
    """Đưa công thức còn `ocr_queued` về `ocr_failed` để người dùng bấm Thử lại."""
    queued_formulas = (
        db.query(FormulaEntry)
        .filter(
            FormulaEntry.document_id == document_id,
            FormulaEntry.status == "ocr_queued",
        )
        .all()
    )
    for formula in queued_formulas:
        formula.status = "ocr_failed"
    document = db.get(Document, document_id)
    if document is not None and document.status == "ocr_processing":
        document.status = "ocr_completed_with_errors"
    db.commit()


def mark_ocr_job_failed(job, connection, type, value, traceback) -> None:
    """RQ failure callback: job OCR lỗi, quá timeout hoặc bị bỏ rơi khi worker chết."""
    db = SessionLocal()
    try:
        _fail_queued_formulas(db, job.args[0])
    except Exception:
        db.rollback()
        logger.exception("Could not mark OCR job %s as failed", job.id)
    finally:
        db.close()


def process_formula_ocr(document_id: UUID) -> None:
    db = SessionLocal()
    try:
        formulas = (
            db.query(FormulaEntry)
            .filter(
                FormulaEntry.document_id == document_id,
                FormulaEntry.status == "ocr_queued",
            )
            .order_by(FormulaEntry.page_number, FormulaEntry.created_at)
            .all()
        )
        model = _load_ocr_model()
        for formula in formulas:
            # Job trùng/chạy lại: bỏ qua công thức đã được job khác xử lý.
            db.refresh(formula)
            if formula.status != "ocr_queued":
                continue
            try:
                with Image.open(Path(formula.image_path)) as image:
                    formula.latex_raw = model(image.convert("RGB"))
                formula.ocr_backend = "pix2tex"
                formula.status = "ocr_complete"
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("OCR failed for formula %s", formula.id)
                failed_formula = db.get(FormulaEntry, formula.id)
                if failed_formula is not None:
                    failed_formula.status = "ocr_failed"
                    db.commit()

        document = db.get(Document, document_id)
        if document is not None:
            remaining_failures = (
                db.query(FormulaEntry)
                .filter(
                    FormulaEntry.document_id == document_id,
                    FormulaEntry.status == "ocr_failed",
                )
                .count()
            )
            document.status = "ocr_completed_with_errors" if remaining_failures else "ocr_complete"
            db.commit()
    except Exception:
        db.rollback()
        logger.exception("OCR job failed for document %s", document_id)
        _fail_queued_formulas(db, document_id)
    finally:
        db.close()