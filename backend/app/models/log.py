import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String, nullable=False)  # vd: "upload", "process", "submit"
    ref_id = Column(UUID(as_uuid=True), nullable=True)  # id của document/formula liên quan

    # JSONB: kiểu dữ liệu đặc biệt của PostgreSQL, lưu được cả 1 object JSON
    # linh hoạt (vd: {"error": "...", "duration_ms": 120}) mà không cần tạo thêm cột riêng
    detail = Column(JSONB, nullable=True)

    # Người thực hiện hành động; NULL với log hệ thống/worker hoặc khi user bị xóa.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))