import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_owned_document
from app.core import storage
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import FormulaEntry, User
from app.schemas.formula import FormulaRegionCreate, FormulaRegionUpdate, FormulaSubmit
from app.services import action_log
from app.services.formula_regions import InvalidRegion, save_formula_crop, validate_bounds
from app.services.ocr_queue import QueueUnavailable, enqueue_ocr

router = APIRouter(prefix="/api/documents", tags=["formulas"])

OCR_QUEUE_UNAVAILABLE = "Không thể đưa OCR vào hàng xử lý"


@router.post("/{document_id}/formulas/recognize", status_code=202)
def recognize_formula_regions(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = get_owned_document(document_id, current_user, db, lock=True)
    if document.status != "formula_proposals_ready":
        raise HTTPException(status_code=409, detail="Tài liệu chưa sẵn sàng chạy OCR")

    formulas = (
        db.query(FormulaEntry)
        .filter(FormulaEntry.document_id == document_id, FormulaEntry.status == "proposed")
        .all()
    )
    if not formulas:
        raise HTTPException(status_code=422, detail="Tài liệu chưa có vùng công thức")

    try:
        enqueue_ocr(
            db,
            document,
            formulas,
            restore_formula_status="proposed",
            restore_document_status="formula_proposals_ready",
            user_id=current_user.id,
            queued_action="recognize_queued",
            failed_action="recognize_job_failed",
        )
    except QueueUnavailable as error:
        raise HTTPException(status_code=503, detail=OCR_QUEUE_UNAVAILABLE) from error
    return {"document_id": document_id, "status": document.status, "queued_count": len(formulas)}


@router.post("/{document_id}/formulas/retry", status_code=202)
def retry_failed_formula_ocr(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = get_owned_document(document_id, current_user, db, lock=True)
    if document.status not in {"ocr_completed_with_errors", "processing_failed"}:
        raise HTTPException(status_code=409, detail="Tài liệu chưa có lỗi OCR để thử lại")

    failed_formulas = (
        db.query(FormulaEntry)
        .filter(FormulaEntry.document_id == document_id, FormulaEntry.status == "ocr_failed")
        .all()
    )
    if not failed_formulas:
        raise HTTPException(status_code=422, detail="Không có công thức OCR lỗi để thử lại")

    try:
        enqueue_ocr(
            db,
            document,
            failed_formulas,
            restore_formula_status="ocr_failed",
            restore_document_status="ocr_completed_with_errors",
            user_id=current_user.id,
            queued_action="retry_queued",
            failed_action="retry_job_failed",
        )
    except QueueUnavailable as error:
        raise HTTPException(status_code=503, detail=OCR_QUEUE_UNAVAILABLE) from error
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
    document = get_owned_document(document_id, current_user, db)

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
    document = get_owned_document(document_id, current_user, db)
    if document.status != "formula_proposals_ready":
        raise HTTPException(status_code=409, detail="Tài liệu chưa sẵn sàng chỉnh vùng")

    page_path = storage.page_image_path(document_id, region.page_number)
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")
    bounds = (region.x_min, region.y_min, region.x_max, region.y_max)
    _validate_bounds(page_path, bounds)

    formula_id = uuid.uuid4()
    crop_path = storage.formula_crop_path(document_id, formula_id)
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
    get_owned_document(document_id, current_user, db)
    formula = _get_proposed_formula(document_id, formula_id, db)
    page_path = storage.page_image_path(document_id, formula.page_number)
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
    get_owned_document(document_id, current_user, db)
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
    get_owned_document(document_id, current_user, db)
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
    get_owned_document(document_id, current_user, db)
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

    # latex_raw không bao giờ bị ghi ở đây: Submit chỉ cập nhật latex_final.
    formula.latex_final = submission.latex_final
    formula.status = "submitted"
    db.commit()
    db.refresh(formula)
    action_log.log_action(db, "submit", formula_id, {"document_id": str(document_id)}, current_user.id)
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


def _validate_bounds(page_path: Path, bounds: tuple[int, int, int, int]) -> None:
    try:
        validate_bounds(page_path, bounds)
    except InvalidRegion as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


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
