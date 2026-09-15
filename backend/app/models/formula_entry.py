import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class FormulaEntry(Base):
    __tablename__ = "formula_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ForeignKey("documents.id"): khai báo rõ ràng đây là khoá ngoại,
    # trỏ tới cột id của bảng documents - PostgreSQL sẽ tự kiểm tra
    # ràng buộc này (không cho insert formula_entries với document_id không tồn tại)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)

    page_number = Column(Integer, nullable=True)
    image_path = Column(String, nullable=True)

    # Text thay vì String: không giới hạn độ dài, phù hợp với chuỗi LaTeX
    # có thể rất dài đối với công thức phức tạp
    latex_raw = Column(Text, nullable=True)
    latex_final = Column(Text, nullable=True)

    ocr_backend = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))