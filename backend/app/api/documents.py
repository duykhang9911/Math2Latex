from pathlib import Path
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Document
from app.schemas.document import DocumentUploadResponse

# APIRouter: một "app FastAPI thu nhỏ", cho phép định nghĩa route ở file riêng
# rồi "gắn" vào app chính trong main.py - giúp main.py không bị phình to
router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = Path("/app/uploads")
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

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng không hỗ trợ: {file_ext}. Chỉ nhận: {sorted(ALLOWED_EXTS)}",
        )

    # Bước A: lưu file vật lý 
    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    # Bước B: lưu metadata vào database 
    new_document = Document(filename=file.filename, status="uploaded")
    db.add(new_document)      # đánh dấu "sẽ thêm" record này
    db.commit()                # thực sự ghi xuống database
    db.refresh(new_document)   # đọc lại record vừa lưu (để lấy id đã tự sinh)

    return {"document_id": new_document.id, "status": new_document.status}