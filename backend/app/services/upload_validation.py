import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.core.limits import MAX_FILENAME_LENGTH, MAX_PAGE_PIXELS, MAX_PDF_PAGES, RENDER_DPI

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


class PdfRejected(Exception):
    """PDF không được chấp nhận; `reason` là một trong: invalid, encrypted, too_many_pages, page_too_large."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


@dataclass(frozen=True)
class PdfInfo:
    page_count: int


def sanitize_filename(raw_name: str) -> str:
    """Chỉ giữ tên file: bỏ thư mục, ký tự điều khiển, khoảng trắng/dấu chấm thừa; cắt theo độ dài tối đa."""
    name = raw_name.replace("\\", "/").rsplit("/", 1)[-1]
    name = _CONTROL_CHARACTERS.sub("", name).strip().rstrip(". ")
    if len(name) > MAX_FILENAME_LENGTH:
        suffix = Path(name).suffix
        name = name[: MAX_FILENAME_LENGTH - len(suffix)] + suffix
    return name


def inspect_pdf(pdf_path: Path) -> PdfInfo:
    """Mở PDF đã lưu và kiểm tra: đúng định dạng PDF, không cần mật khẩu, số trang và kích thước trang trong giới hạn."""
    try:
        document = pymupdf.open(pdf_path, filetype="pdf")
    except Exception:
        raise PdfRejected("invalid", "File không phải PDF hợp lệ hoặc đã bị hỏng") from None

    with document:
        # PyMuPDF mở cả ảnh/XPS/EPUB... ngay cả khi ép filetype="pdf"; chỉ nhận PDF thật.
        if not document.is_pdf:
            raise PdfRejected("invalid", "File không phải PDF hợp lệ hoặc đã bị hỏng")
        if document.needs_pass and not document.authenticate(""):
            raise PdfRejected("encrypted", "PDF được bảo vệ bằng mật khẩu, không thể xử lý")
        try:
            page_count = len(document)
            if page_count == 0:
                raise PdfRejected("invalid", "PDF không có trang nào")
            if page_count > MAX_PDF_PAGES:
                raise PdfRejected("too_many_pages", f"PDF có {page_count} trang; tối đa {MAX_PDF_PAGES} trang")

            scale = RENDER_DPI / 72
            for page_index in range(page_count):
                rect = document[page_index].rect
                if rect.width * scale * rect.height * scale > MAX_PAGE_PIXELS:
                    raise PdfRejected(
                        "page_too_large",
                        f"Trang {page_index + 1} quá lớn để xử lý (tối đa {MAX_PAGE_PIXELS:,} pixel khi render)",
                    )
        except PdfRejected:
            raise
        except Exception:
            raise PdfRejected("invalid", "File không phải PDF hợp lệ hoặc đã bị hỏng") from None
    return PdfInfo(page_count=page_count)
