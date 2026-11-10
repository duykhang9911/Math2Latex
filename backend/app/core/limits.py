"""Giới hạn upload/xử lý; mỗi giá trị đổi được bằng biến môi trường.

Mặc định chọn theo số đo trên CPU (xem Docs/ARCHITECTURE.md, mục "Cấu hình suy luận"): detect ≈ 0,64 s/trang,
OCR ≈ 0,23 s/công thức. Timeout để dư nhiều lần so với số đo để máy chậm hơn vẫn xử lý xong.
"""
import os


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


MAX_FILE_SIZE = _int_env("MAX_UPLOAD_MB", 100) * 1024 * 1024
MAX_PDF_PAGES = _int_env("MAX_PDF_PAGES", 200)
# Số pixel tối đa của một trang khi render ở RENDER_DPI (A4 ở 150 dpi ≈ 2,2 triệu pixel).
MAX_PAGE_PIXELS = _int_env("MAX_PAGE_PIXELS", 25_000_000)
RENDER_DPI = 150
MAX_FILENAME_LENGTH = 255

PDF_JOB_TIMEOUT_SECONDS = _int_env("PDF_JOB_TIMEOUT_SECONDS", 1800)
OCR_JOB_TIMEOUT_SECONDS = _int_env("OCR_JOB_TIMEOUT_SECONDS", 3600)

# Đăng nhập sai: tối đa N lần cho mỗi (IP, username) và M lần cho mỗi IP trong một cửa sổ; vượt thì trả 429.
LOGIN_MAX_FAILURES = _int_env("LOGIN_MAX_FAILURES", 5)
LOGIN_IP_MAX_FAILURES = _int_env("LOGIN_IP_MAX_FAILURES", 30)
LOGIN_WINDOW_SECONDS = _int_env("LOGIN_WINDOW_SECONDS", 900)
