import shutil
import uuid
import logging
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, File, Query, Response, UploadFile, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from PIL import Image

from app.api.deps import get_owned_document
from app.core import queue, storage
from app.core.database import get_db
from app.core.limits import MAX_FILE_SIZE, PDF_JOB_TIMEOUT_SECONDS
from app.core.security import get_current_user
from app.models import Document, FormulaEntry, User
from app.schemas.document import DocumentListResponse, DocumentSummary, DocumentUploadResponse
from app.services import action_log
from app.services.document_queries import BUSY_STATUSES, summary, summary_query
from app.services.latex_export import build_latex_export
from app.services.pdf_pages import mark_pdf_job_failed, process_pdf_pages
from app.services.upload_validation import PdfRejected, inspect_pdf, sanitize_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTS = {".pdf"}
UPLOAD_REJECTION_STATUS = {"invalid": 400, "encrypted": 400, "too_many_pages": 422, "page_too_large": 422}
MAX_HISTORY_PAGE_SIZE = 100


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Chưa chọn file")

    safe_filename = sanitize_filename(file.filename)
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
    document_dir = storage.document_dir(document_id)
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
        pdf_info = await run_in_threadpool(inspect_pdf, save_path)
    except PdfRejected as rejected:
        shutil.rmtree(document_dir, ignore_errors=True)
        raise HTTPException(status_code=UPLOAD_REJECTION_STATUS[rejected.reason], detail=rejected.message) from None
    except HTTPException:
        shutil.rmtree(document_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(document_dir, ignore_errors=True)
        logger.error(f"Error writing file: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lưu file")

    new_document = Document(
        id=document_id,
        filename=safe_filename,
        status="processing_pages",
        uploaded_by=current_user.id,
        file_size_bytes=bytes_written,
        page_count=pdf_info.page_count,
    )
    try:
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        action_log.log_action(
            db, "upload", document_id, {"filename": safe_filename, "size_bytes": bytes_written}, current_user.id
        )
    except Exception as e:
        db.rollback()
        shutil.rmtree(document_dir, ignore_errors=True)
        logger.error(f"Error creating document record: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lưu thông tin tài liệu")

    try:
        queue.enqueue_job(
            process_pdf_pages,
            document_id,
            save_path,
            on_failure=mark_pdf_job_failed,
            job_timeout=PDF_JOB_TIMEOUT_SECONDS,
        )
    except Exception as error:
        db.query(Document).filter(Document.id == document_id).update({"status": "processing_failed"})
        db.commit()
        action_log.log_action(db, "upload_job_failed", document_id, {"error": str(error)}, current_user.id)
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
        summary_query(db)
        .filter(*filters)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    action_log.log_action(
        db,
        "history_list",
        detail={"limit": limit, "offset": offset, "status": status},
        user_id=current_user.id,
    )
    return {
        "items": [summary(*row) for row in rows],
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
        summary_query(db)
        .filter(Document.id == document_id, Document.uploaded_by == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    action_log.log_action(db, "history_open", document_id, user_id=current_user.id)
    return summary(*row)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = get_owned_document(document_id, current_user, db, lock=True)
    if document.status in BUSY_STATUSES:
        raise HTTPException(status_code=409, detail="Tài liệu đang được xử lý, chưa thể xóa")

    filename = document.filename
    # formula_entries.document_id không có ON DELETE CASCADE nên xóa công thức trước.
    db.query(FormulaEntry).filter(FormulaEntry.document_id == document_id).delete(
        synchronize_session=False
    )
    db.delete(document)
    db.commit()
    action_log.log_action(db, "history_delete", document_id, {"filename": filename}, current_user.id)

    document_dir = storage.document_dir(document_id)
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
    document = get_owned_document(document_id, current_user, db)
    source_path = storage.source_pdf_path(document_id)
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Không còn file PDF gốc")
    action_log.log_action(db, "download_source", document_id, user_id=current_user.id)
    return FileResponse(source_path, media_type="application/pdf", filename=document.filename)


@router.get("/{document_id}/export")
def export_submitted_latex(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = get_owned_document(document_id, current_user, db)
    formulas = (
        db.query(FormulaEntry)
        .filter(FormulaEntry.document_id == document_id, FormulaEntry.status == "submitted")
        .order_by(FormulaEntry.page_number, FormulaEntry.created_at)
        .all()
    )
    if not formulas:
        raise HTTPException(status_code=409, detail="Chưa có công thức nào được Submit")

    action_log.log_action(db, "export_latex", document_id, {"formula_count": len(formulas)}, current_user.id)
    export_name = quote(f"{Path(document.filename).stem}.tex")
    return Response(
        content=build_latex_export(formulas),
        media_type="text/x-tex",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{export_name}"},
    )


@router.get("/{document_id}/pages")
def list_document_pages(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = get_owned_document(document_id, current_user, db)

    page_files = sorted(storage.pages_dir(document_id).glob("page-*.png"))
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
    get_owned_document(document_id, current_user, db)
    if page_number < 1:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")

    page_path = storage.page_image_path(document_id, page_number)
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")
    return FileResponse(page_path, media_type="image/png")
