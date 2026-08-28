from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Khởi tạo app - đây là điểm trung tâm, mọi route (endpoint) sau này đều "gắn" vào biến app này
app = FastAPI(title="Math2Latex API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Endpoint kiểm tra sức khoẻ hệ thống - quy ước phổ biến trong mọi API thực tế,
# dùng để: (1) tự kiểm tra backend còn sống không, (2) sau này Docker/hạ tầng
# có thể tự động ping route này để biết container có "khoẻ" không
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        return {"status": "error", "message": "No file selected"}

    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_exts:
        return {
            "status": "error",
            "message": f"Unsupported file type: {file_ext}. Allowed: {sorted(allowed_exts)}",
        }

    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "size": len(content),
        "path": str(save_path),
    }
