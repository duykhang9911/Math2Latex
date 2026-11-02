import os
import shutil
import uuid
import logging
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, File, Query, Response, UploadFile, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from PIL import Image

from app.core.database import get_db
from app.models import Document, FormulaEntry, Log
from app.core.queue import enqueue_job
from app.core.security import get_current_user
from app.services.pdf_pages import process_pdf_pages
from app.schemas.document import DocumentListResponse, DocumentSummary, DocumentUploadResponse
from app.schemas.formula import FormulaRegionCreate, FormulaRegionUpdate, FormulaSubmit
from app.services.formula_ocr import process_formula_ocr
from app.services.formula_regions import save_formula_crop
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTS = {".pdf"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_HISTORY_PAGE_SIZE = 100
# Đang có job worker ghi vào thư mục tài liệu; không cho xóa trong lúc này.
BUSY_STATUSES = {"processing_pages", "detecting_formulas", "ocr_processing"}


def _log_action(
    db: Session,
    action: str,
    ref_id: uuid.UUID = None,
    detail: dict = None,
    user_id: uuid.UUID = None,
) -> None:
    log_entry = Log(action=action, ref_id=ref_id, detail=detail, user_id=user_id)
    db.add(log_entry)
    db.commit()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Chưa chọn file")

    safe_filename = file.filename.replace("\\", "/").rsplit("/", 1)[-1]
    file_ext = Path(safe_filename).suffix.lower()
    if file_ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ nhận PDF. Định dạng nhận được: {file_ext}",
        )

    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File quá lớn. Tối đa {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    document_id = uuid.uuid4()
    document_dir = UPLOAD_DIR / str(document_id)
    document_dir.mkdir(parents=True, exist_ok=True)
    save_path = document_dir / f"source{file_ext}"

    try:
        bytes_written = 0
        with open(save_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail=f"File quá lớn. Tối đa {MAX_FILE_SIZE // (1024 * 1024)}MB")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        save_path.unlink(missing_ok=True)
        document_dir.rmdir()
        logger.error(f"Error writing file: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lưu file")

    new_document = Document(
        id=document_id,
        filename=safe_filename,
        status="processing_pages",
        uploaded_by=current_user.id,
        file_size_bytes=bytes_written,
    )
    try:
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        _log_action(db, "upload", document_id, {"filename": safe_filename, "size_bytes": bytes_written}, current_user.id)
    except Exception as e:
        db.rollback()
        save_path.unlink(missing_ok=True)
        document_dir.rmdir()
        logger.error(f"Error creating document record: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lưu thông tin tài liệu")

    try:
        enqueue_job(process_pdf_pages, document_id, save_path)
    except Exception as error:
        db.query(Document).filter(Document.id == document_id).update({"status": "processing_failed"})
        db.commit()
        _log_action(db, "upload_job_failed", document_id, {"error": str(error)}, current_user.id)
        logger.error(f"Error queueing PDF processing: {error}")
        raise HTTPException(status_code=503, detail="Không thể đưa PDF vào hàng xử lý") from error

    return {"document_id": new_document.id, "status": new_document.status}


@router.get("", response_model=DocumentListResponse)
def list_documents(
    limit: int = Query(20, ge=1, le=MAX_HISTORY_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = [Document.uploaded_by == current_user.id]
    if status:
        filters.append(Document.status == status)

    total = db.query(func.count(Document.id)).filter(*filters).scalar()
    rows = (
        _document_summary_query(db)
        .filter(*filters)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    _log_action(
        db,
        "history_list",
        detail={"limit": limit, "offset": offset, "status": status},
        user_id=current_user.id,
    )
    return {
        "items": [_document_summary(*row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{document_id}", response_model=DocumentSummary)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        _document_summary_query(db)
        .filter(Document.id == document_id, Document.uploaded_by == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    _log_action(db, "history_open", document_id, user_id=current_user.id)
    return _document_summary(*row)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.uploaded_by == current_user.id)
        .with_for_update()
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    if document.status in BUSY_STATUSES:
        raise HTTPException(status_code=409, detail="Tài liệu đang được xử lý, chưa thể xóa")

    filename = document.filename
    # formula_entries.document_id không có ON DELETE CASCADE nên xóa công thức trước.
    db.query(FormulaEntry).filter(FormulaEntry.document_id == document_id).delete(
        synchronize_session=False
    )
    db.delete(document)
    db.commit()
    _log_action(db, "history_delete", document_id, {"filename": filename}, current_user.id)

    document_dir = UPLOAD_DIR / str(document_id)
    try:
        if document_dir.exists():
            shutil.rmtree(document_dir)
    except OSError:
        logger.exception("Could not remove files of deleted document %s", document_id)


@router.get("/{document_id}/source")
def download_source_pdf(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)
    source_path = UPLOAD_DIR / str(document_id) / "source.pdf"
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Không còn file PDF gốc")
    _log_action(db, "download_source", document_id, user_id=current_user.id)
    return FileResponse(source_path, media_type="application/pdf", filename=document.filename)


@router.get("/{document_id}/export")
def export_submitted_latex(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)
    formulas = (
        db.query(FormulaEntry)
        .filter(FormulaEntry.document_id == document_id, FormulaEntry.status == "submitted")
        .order_by(FormulaEntry.page_number, FormulaEntry.created_at)
        .all()
    )
    if not formulas:
        raise HTTPException(status_code=409, detail="Chưa có công thức nào được Submit")

    # Chỉ xuất latex_final (nội dung người dùng đã xác nhận), không xuất latex_raw.
    parts = ["% Math2Latex export - submitted formulas only"]
    for index, formula in enumerate(formulas, start=1):
        parts.append(f"\n% Page {formula.page_number} - formula {index}\n\\[\n{formula.latex_final or ''}\n\\]")
    body = "\n".join(parts) + "\n"

    _log_action(db, "export_latex", document_id, {"formula_count": len(formulas)}, current_user.id)
    export_name = quote(f"{Path(document.filename).stem}.tex")
    return Response(
        content=body,
        media_type="text/x-tex",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{export_name}"},
    )


@router.get("/{document_id}/pages")
def list_document_pages(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)

    pages_dir = UPLOAD_DIR / str(document_id) / "pages"
    page_files = sorted(pages_dir.glob("page-*.png"))
    pages = []
    for page_path in page_files:
        with Image.open(page_path) as page_image:
            width, height = page_image.size
        page_number = int(page_path.stem.removeprefix("page-"))
        pages.append(
            {
                "page_number": page_number,
                "width": width,
                "height": height,
                "image_url": f"/api/documents/{document_id}/pages/{page_number}",
            }
        )
    return {
        "document_id": document_id,
        "status": document.status,
        "pages": pages,
    }


@router.get("/{document_id}/pages/{page_number}")
def get_document_page(
    document_id: uuid.UUID,
    page_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_document(document_id, current_user, db)
    if page_number < 1:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")

    page_path = UPLOAD_DIR / str(document_id) / "pages" / f"page-{page_number:06d}.png"
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")
    return FileResponse(page_path, media_type="image/png")


@router.post("/{document_id}/formulas/recognize", status_code=202)
def recognize_formula_regions(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.uploaded_by == current_user.id)
        .with_for_update()
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    if document.status != "formula_proposals_ready":
        raise HTTPException(status_code=409, detail="Tài liệu chưa sẵn sàng chạy OCR")

    formulas = (
        db.query(FormulaEntry)
        .filter(FormulaEntry.document_id == document_id, FormulaEntry.status == "proposed")
        .all()
    )
    if not formulas:
        raise HTTPException(status_code=422, detail="Tài liệu chưa có vùng công thức")

    for formula in formulas:
        formula.status = "ocr_queued"
    document.status = "ocr_processing"
    db.commit()
    try:
        enqueue_job(process_formula_ocr, document_id)
        _log_action(db, "recognize_queued", document_id, {"formula_count": len(formulas)}, current_user.id)
    except Exception as error:
        for formula in formulas:
            formula.status = "proposed"
        document.status = "formula_proposals_ready"
        db.commit()
        _log_action(db, "recognize_job_failed", document_id, {"error": str(error)}, current_user.id)
        logger.error(f"Error queueing OCR: {error}")
        raise HTTPException(status_code=503, detail="Không thể đưa OCR vào hàng xử lý") from error
    return {"document_id": document_id, "status": document.status, "queued_count": len(formulas)}


@router.post("/{document_id}/formulas/retry", status_code=202)
def retry_failed_formula_ocr(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.uploaded_by == current_user.id)
        .with_for_update()
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    if document.status not in {"ocr_completed_with_errors", "processing_failed"}:
        raise HTTPException(status_code=409, detail="Tài liệu chưa có lỗi OCR để thử lại")

    failed_formulas = (
        db.query(FormulaEntry)
        .filter(FormulaEntry.document_id == document_id, FormulaEntry.status == "ocr_failed")
        .all()
    )
    if not failed_formulas:
        raise HTTPException(status_code=422, detail="Không có công thức OCR lỗi để thử lại")

    for formula in failed_formulas:
        formula.status = "ocr_queued"
    document.status = "ocr_processing"
    db.commit()
    try:
        enqueue_job(process_formula_ocr, document_id)
        _log_action(db, "retry_queued", document_id, {"formula_count": len(failed_formulas)}, current_user.id)
    except Exception as error:
        for formula in failed_formulas:
            formula.status = "ocr_failed"
        document.status = "ocr_completed_with_errors"
        db.commit()
        _log_action(db, "retry_job_failed", document_id, {"error": str(error)}, current_user.id)
        logger.error(f"Error queueing retry: {error}")
        raise HTTPException(status_code=503, detail="Không thể đưa OCR vào hàng xử lý") from error
    return {
        "document_id": document_id,
        "status": document.status,
        "queued_count": len(failed_formulas),
    }


@router.get("/{document_id}/formulas")
def list_formula_regions(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)

    formulas = (
        db.query(FormulaEntry)
        .filter(FormulaEntry.document_id == document_id)
        .order_by(FormulaEntry.page_number, FormulaEntry.created_at)
        .all()
    )
    return {
        "document_id": document_id,
        "status": document.status,
        "formulas": [_formula_region_response(formula) for formula in formulas],
    }


@router.post("/{document_id}/formulas", status_code=201)
def create_formula_region(
    document_id: uuid.UUID,
    region: FormulaRegionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)
    if document.status != "formula_proposals_ready":
        raise HTTPException(status_code=409, detail="Tài liệu chưa sẵn sàng chỉnh vùng")

    page_path = _page_path(document_id, region.page_number)
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")
    bounds = (region.x_min, region.y_min, region.x_max, region.y_max)
    _validate_bounds(page_path, bounds)

    formula_id = uuid.uuid4()
    crop_path = UPLOAD_DIR / str(document_id) / "formulas" / f"{formula_id}.png"
    save_formula_crop(page_path, bounds, crop_path)
    formula = FormulaEntry(
        id=formula_id,
        document_id=document_id,
        page_number=region.page_number,
        image_path=str(crop_path),
        x_min=region.x_min,
        y_min=region.y_min,
        x_max=region.x_max,
        y_max=region.y_max,
        status="proposed",
    )
    db.add(formula)
    db.commit()
    db.refresh(formula)
    return _formula_region_response(formula)


@router.patch("/{document_id}/formulas/{formula_id}")
def update_formula_region(
    document_id: uuid.UUID,
    formula_id: uuid.UUID,
    region: FormulaRegionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_document(document_id, current_user, db)
    formula = _get_proposed_formula(document_id, formula_id, db)
    page_path = _page_path(document_id, formula.page_number)
    bounds = (region.x_min, region.y_min, region.x_max, region.y_max)
    _validate_bounds(page_path, bounds)

    formula.x_min, formula.y_min, formula.x_max, formula.y_max = bounds
    save_formula_crop(page_path, bounds, Path(formula.image_path))
    db.commit()
    db.refresh(formula)
    return _formula_region_response(formula)


@router.delete("/{document_id}/formulas/{formula_id}", status_code=204)
def delete_formula_region(
    document_id: uuid.UUID,
    formula_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_document(document_id, current_user, db)
    formula = _get_proposed_formula(document_id, formula_id, db)
    Path(formula.image_path).unlink(missing_ok=True)
    db.delete(formula)
    db.commit()


@router.get("/{document_id}/formulas/{formula_id}/image")
def get_formula_image(
    document_id: uuid.UUID,
    formula_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_document(document_id, current_user, db)
    formula = (
        db.query(FormulaEntry)
        .filter(
            FormulaEntry.id == formula_id,
            FormulaEntry.document_id == document_id,
        )
        .first()
    )
    if formula is None or not formula.image_path or not Path(formula.image_path).is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh công thức")
    return FileResponse(formula.image_path, media_type="image/png")


@router.post("/{document_id}/formulas/{formula_id}/submit")
def submit_formula(
    document_id: uuid.UUID,
    formula_id: uuid.UUID,
    submission: FormulaSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_document(document_id, current_user, db)
    formula = (
        db.query(FormulaEntry)
        .filter(
            FormulaEntry.id == formula_id,
            FormulaEntry.document_id == document_id,
        )
        .first()
    )
    if formula is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy công thức")
    if formula.status not in {"ocr_complete", "submitted"}:
        raise HTTPException(status_code=409, detail="Công thức chưa sẵn sàng để gửi")

    formula.latex_final = submission.latex_final
    formula.status = "submitted"
    db.commit()
    db.refresh(formula)
    _log_action(db, "submit", formula_id, {"document_id": str(document_id)}, current_user.id)
    return {
        "formula_id": formula.id,
        "latex_raw": formula.latex_raw,
        "latex_final": formula.latex_final,
        "status": formula.status,
    }


def _document_summary_query(db: Session):
    counts = (
        db.query(
            FormulaEntry.document_id.label("document_id"),
            func.count(FormulaEntry.id).label("formula_count"),
            func.count(case((FormulaEntry.status == "submitted", 1))).label("submitted_count"),
        )
        .group_by(FormulaEntry.document_id)
        .subquery()
    )
    return db.query(
        Document,
        func.coalesce(counts.c.formula_count, 0),
        func.coalesce(counts.c.submitted_count, 0),
    ).outerjoin(counts, counts.c.document_id == Document.id)


def _document_summary(document: Document, formula_count: int, submitted_count: int) -> dict:
    return {
        "document_id": document.id,
        "filename": document.filename,
        "status": document.status,
        "file_size_bytes": document.file_size_bytes,
        "page_count": document.page_count,
        "formula_count": formula_count,
        "submitted_count": submitted_count,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _formula_region_response(formula: FormulaEntry) -> dict:
    return {
        "formula_id": formula.id,
        "page_number": formula.page_number,
        "bounds": {
            "x_min": formula.x_min,
            "y_min": formula.y_min,
            "x_max": formula.x_max,
            "y_max": formula.y_max,
        },
        "confidence": formula.confidence,
        "status": formula.status,
        "latex_raw": formula.latex_raw,
        "latex_final": formula.latex_final,
        "image_url": (
            f"/api/documents/{formula.document_id}/formulas/{formula.id}/image"
            f"?v={formula.x_min}-{formula.y_min}-{formula.x_max}-{formula.y_max}"
        ),
    }


def _page_path(document_id: uuid.UUID, page_number: int) -> Path:
    return UPLOAD_DIR / str(document_id) / "pages" / f"page-{page_number:06d}.png"


def _get_owned_document(document_id: uuid.UUID, user: User, db: Session) -> Document:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.uploaded_by == user.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return document


def _validate_bounds(page_path: Path, bounds: tuple[int, int, int, int]) -> None:
    x_min, y_min, x_max, y_max = bounds
    if x_max <= x_min or y_max <= y_min:
        raise HTTPException(status_code=422, detail="Vùng công thức phải có chiều rộng và cao dương")
    with Image.open(page_path) as page_image:
        image_width, image_height = page_image.size
    if x_max > image_width or y_max > image_height:
        raise HTTPException(status_code=422, detail="Vùng công thức vượt ngoài kích thước trang")


def _get_proposed_formula(
    document_id: uuid.UUID,
    formula_id: uuid.UUID,
    db: Session,
) -> FormulaEntry:
    formula = (
        db.query(FormulaEntry)
        .filter(
            FormulaEntry.id == formula_id,
            FormulaEntry.document_id == document_id,
        )
        .first()
    )
    if formula is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy vùng công thức")
    if formula.status != "proposed":
        raise HTTPException(status_code=409, detail="Chỉ chỉnh sửa được vùng đang ở trạng thái đề xuất")
    return formula