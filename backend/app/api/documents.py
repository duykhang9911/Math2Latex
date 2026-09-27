import os
import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from PIL import Image

from app.core.database import get_db
from app.models import Document, FormulaEntry
from app.core.queue import enqueue_job
from app.services.pdf_pages import process_pdf_pages
from app.schemas.formula import FormulaRegionCreate, FormulaRegionUpdate, FormulaSubmit
from app.services.formula_ocr import process_formula_ocr
from app.services.formula_regions import save_formula_crop

# APIRouter: một "app FastAPI thu nhỏ", cho phép định nghĩa route ở file riêng
# rồi "gắn" vào app chính trong main.py - giúp main.py không bị phình to
router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg"}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),  # Depends(get_db): FastAPI tự gọi get_db() 
                                     # để lấy 1 session DB cho riêng request này
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Chưa chọn file")

    safe_filename = file.filename.replace("\\", "/").rsplit("/", 1)[-1]
    file_ext = Path(safe_filename).suffix.lower()
    if file_ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng không hỗ trợ: {file_ext}. Chỉ nhận: {sorted(ALLOWED_EXTS)}",
        )

    document_id = uuid.uuid4()
    document_dir = UPLOAD_DIR / str(document_id)
    document_dir.mkdir(parents=True, exist_ok=True)
    save_path = document_dir / f"source{file_ext}"
    content = await file.read()
    save_path.write_bytes(content)

    initial_status = "processing_pages" if file_ext == ".pdf" else "uploaded"
    new_document = Document(
        id=document_id,
        filename=safe_filename,
        status=initial_status,
    )
    try:
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
    except Exception:
        db.rollback()
        save_path.unlink(missing_ok=True)
        document_dir.rmdir()
        raise

    if file_ext == ".pdf":
        try:
            enqueue_job(process_pdf_pages, document_id, save_path)
        except Exception as error:
            db.query(Document).filter(Document.id == document_id).update({"status": "processing_failed"})
            db.commit()
            raise HTTPException(status_code=503, detail="Không thể đưa PDF vào hàng xử lý") from error

    return {"document_id": new_document.id, "status": new_document.status}


@router.get("/{document_id}/pages")
def list_document_pages(document_id: uuid.UUID, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

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
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    if page_number < 1:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")

    page_path = UPLOAD_DIR / str(document_id) / "pages" / f"page-{page_number:06d}.png"
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")
    return FileResponse(page_path, media_type="image/png")


@router.post("/{document_id}/formulas/recognize", status_code=202)
def recognize_formula_regions(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
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
    except Exception as error:
        for formula in formulas:
            formula.status = "proposed"
        document.status = "formula_proposals_ready"
        db.commit()
        raise HTTPException(status_code=503, detail="Không thể đưa OCR vào hàng xử lý") from error
    return {"document_id": document_id, "status": document.status, "queued_count": len(formulas)}


@router.post("/{document_id}/formulas/retry", status_code=202)
def retry_failed_formula_ocr(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
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
    except Exception as error:
        for formula in failed_formulas:
            formula.status = "ocr_failed"
        document.status = "ocr_completed_with_errors"
        db.commit()
        raise HTTPException(status_code=503, detail="Không thể đưa OCR vào hàng xử lý") from error
    return {
        "document_id": document_id,
        "status": document.status,
        "queued_count": len(failed_formulas),
    }


@router.get("/{document_id}/formulas")
def list_formula_regions(document_id: uuid.UUID, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

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
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
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
    db: Session = Depends(get_db),
):
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
    db: Session = Depends(get_db),
):
    formula = _get_proposed_formula(document_id, formula_id, db)
    Path(formula.image_path).unlink(missing_ok=True)
    db.delete(formula)
    db.commit()


@router.get("/{document_id}/formulas/{formula_id}/image")
def get_formula_image(
    document_id: uuid.UUID,
    formula_id: uuid.UUID,
    db: Session = Depends(get_db),
):
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
    db: Session = Depends(get_db),
):
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
    return {
        "formula_id": formula.id,
        "latex_raw": formula.latex_raw,
        "latex_final": formula.latex_final,
        "status": formula.status,
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