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
        if document is not None:
            document.status = "ocr_completed_with_errors"
            db.commit()
    finally:
        db.close()