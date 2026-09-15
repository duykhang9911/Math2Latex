import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Đọc chuỗi kết nối DB từ biến môi trường (đã khai báo sẵn trong docker-compose.yml
# ở mục "environment: DB_URL: ..."). Không viết cứng (hard-code) mật khẩu vào đây.
DATABASE_URL = os.getenv("DB_URL")

# engine: đối tượng đại diện cho "kết nối" tới database, SQLAlchemy dùng nó
# để thực sự gửi câu lệnh SQL xuống Postgres
engine = create_engine(DATABASE_URL)

# SessionLocal: mỗi lần xử lý 1 request, ta sẽ tạo 1 "phiên làm việc" (session)
# riêng với DB từ đây - tránh việc nhiều request dùng chung 1 kết nối gây xung đột
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: lớp gốc mà mọi model (bảng) trong models/ sẽ kế thừa từ đây
# SQLAlchemy dựa vào Base để biết "có những bảng nào" khi tạo migration
Base = declarative_base()


def get_db():
    """
    Hàm này sẽ được inject vào từng API endpoint (Tuần 2, bước 7-8).
    Nó tạo 1 session mới cho mỗi request, và luôn đóng lại sau khi xong -
    kể cả khi có lỗi xảy ra giữa chừng (nhờ try/finally).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()