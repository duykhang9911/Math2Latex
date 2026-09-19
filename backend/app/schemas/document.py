import uuid
from datetime import datetime
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    """
    Hình dạng dữ liệu trả về cho frontend sau khi upload thành công.
    Đây chính là "hợp đồng" API đã chốt trong file kế hoạch:
    { document_id, status }
    """
    id: uuid.UUID
    status: str

    class Config:
        # Cho phép Pydantic đọc trực tiếp từ object SQLAlchemy (Document)
        # thay vì phải tự tay convert sang dict trước
        from_attributes = True


class DocumentOut(BaseModel):
    """Hình dạng đầy đủ của 1 document khi trả về (dùng cho các API sau này, vd GET list)."""
    id: uuid.UUID
    filename: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True