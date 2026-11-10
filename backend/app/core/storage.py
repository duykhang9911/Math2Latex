import os
from pathlib import Path
from uuid import UUID

# Thư mục lưu file; đọc UPLOAD_DIR lúc import. Test thay `UPLOAD_DIR` bằng thư mục tạm.
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def document_dir(document_id: UUID) -> Path:
    return UPLOAD_DIR / str(document_id)


def source_pdf_path(document_id: UUID) -> Path:
    return document_dir(document_id) / "source.pdf"


def pages_dir(document_id: UUID) -> Path:
    return document_dir(document_id) / "pages"


def page_image_path(document_id: UUID, page_number: int) -> Path:
    return pages_dir(document_id) / f"page-{page_number:06d}.png"


def formula_crop_path(document_id: UUID, formula_id: UUID) -> Path:
    return document_dir(document_id) / "formulas" / f"{formula_id}.png"
