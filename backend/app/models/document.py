import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Document(Base):
    # __tablename__: tên bảng thật sự sẽ xuất hiện trong PostgreSQL
    __tablename__ = "documents"

    # uuid.uuid4 sinh ra 1 mã định danh ngẫu nhiên, gần như không bao giờ trùng -
    # an toàn hơn dùng số đếm 1,2,3... khi sau này có nhiều người dùng cùng lúc
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    filename = Column(String, nullable=False)

    # nullable=False + default: luôn có giá trị mặc định "uploaded" khi mới tạo
    status = Column(String, nullable=False, default="uploaded")

    # để trống FK tới users ở bước này (bảng users tạo ở dưới) - sẽ nối sau
    # khi làm chức năng đăng nhập, hiện tại chưa cần bắt buộc
    uploaded_by = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))