import uuid
from datetime import datetime, timezone
from sqlalchemy import BigInteger, CheckConstraint, Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


# Mọi giá trị status mà API/worker ghi; "uploaded" là giá trị của document tạo trước khi có pipeline nền.
DOCUMENT_STATUSES = (
    "uploaded",
    "processing_pages",
    "detecting_formulas",
    "formula_proposals_ready",
    "ocr_processing",
    "ocr_complete",
    "ocr_completed_with_errors",
    "processing_failed",
)


class Document(Base):
    # __tablename__: tên bảng thật sự sẽ xuất hiện trong PostgreSQL
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN (" + ", ".join(f"'{value}'" for value in DOCUMENT_STATUSES) + ")",
            name="ck_documents_status",
        ),
    )

    # uuid.uuid4 sinh ra 1 mã định danh ngẫu nhiên, gần như không bao giờ trùng -
    # an toàn hơn dùng số đếm 1,2,3... khi sau này có nhiều người dùng cùng lúc
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    filename = Column(String, nullable=False)

    # nullable=False + default: luôn có giá trị mặc định "uploaded" khi mới tạo
    status = Column(String, nullable=False, default="uploaded")

    # Nullable để giữ các document cũ chưa gắn tài khoản; document mới được gắn user đăng nhập.
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata cho lịch sử: file_size_bytes ghi lúc upload, page_count ghi khi worker render xong.
    # Document cũ (trước migration b7c1d2e3f4a5) để NULL.
    file_size_bytes = Column(BigInteger, nullable=True)
    page_count = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )