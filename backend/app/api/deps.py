import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Document, User


def get_owned_document(document_id: uuid.UUID, user: User, db: Session, lock: bool = False) -> Document:
    """Document của chính user; người khác hoặc không tồn tại đều trả 404 (không lộ sự tồn tại).

    `lock=True` khóa dòng (SELECT ... FOR UPDATE) cho các thao tác đổi trạng thái/xóa.
    """
    query = db.query(Document).filter(Document.id == document_id, Document.uploaded_by == user.id)
    if lock:
        query = query.with_for_update()
    document = query.first()
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return document
