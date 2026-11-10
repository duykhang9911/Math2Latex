import logging

from sqlalchemy.orm import Session

from app.core import queue
from app.core.limits import OCR_JOB_TIMEOUT_SECONDS
from app.models import Document, FormulaEntry
from app.services import action_log
from app.services.formula_ocr import mark_ocr_job_failed, process_formula_ocr

logger = logging.getLogger(__name__)


class QueueUnavailable(Exception):
    """Không đưa được job OCR vào hàng đợi; trạng thái đã được hoàn tác."""


def enqueue_ocr(
    db: Session,
    document: Document,
    formulas: list[FormulaEntry],
    *,
    restore_formula_status: str,
    restore_document_status: str,
    user_id,
    queued_action: str,
    failed_action: str,
) -> None:
    """Chuyển công thức sang `ocr_queued`, commit, rồi enqueue job OCR.

    Commit trước khi enqueue để worker luôn thấy trạng thái mới. Nếu enqueue lỗi (Redis down) thì hoàn tác
    về `restore_*` để người dùng gọi lại được; lỗi ghi log sau khi job đã vào queue không hoàn tác gì.
    """
    for formula in formulas:
        formula.status = "ocr_queued"
    document.status = "ocr_processing"
    db.commit()
    try:
        queue.enqueue_job(
            process_formula_ocr,
            document.id,
            on_failure=mark_ocr_job_failed,
            job_timeout=OCR_JOB_TIMEOUT_SECONDS,
        )
    except Exception as error:
        for formula in formulas:
            formula.status = restore_formula_status
        document.status = restore_document_status
        db.commit()
        action_log.log_action(db, failed_action, document.id, {"error": str(error)}, user_id)
        logger.error(f"Error queueing OCR ({failed_action}): {error}")
        raise QueueUnavailable from error
    action_log.log_action_after_enqueue(db, queued_action, document.id, {"formula_count": len(formulas)}, user_id)
