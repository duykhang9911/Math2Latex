import logging
import uuid

from sqlalchemy.orm import Session

from app.models import Log

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    action: str,
    ref_id: uuid.UUID = None,
    detail: dict = None,
    user_id: uuid.UUID = None,
) -> None:
    db.add(Log(action=action, ref_id=ref_id, detail=detail, user_id=user_id))
    db.commit()


def log_action_after_enqueue(db: Session, *args, **kwargs) -> None:
    """Job đã vào queue: lỗi ghi log không được làm hoàn tác trạng thái hay trả lỗi cho người dùng."""
    try:
        log_action(db, *args, **kwargs)
    except Exception:
        db.rollback()
        logger.exception("Could not write action log after the job was queued")
