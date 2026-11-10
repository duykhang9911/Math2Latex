import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.formulas import router as formulas_router

app = FastAPI(title="Math2Latex API")

# Origin của frontend; production đặt CORS_ORIGINS="https://app.example.com" (phân tách bằng dấu phẩy).
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reject_cross_origin_writes(request: Request, call_next):
    """Lớp phòng CSRF thứ hai ngoài SameSite=Lax: request ghi từ origin lạ bị từ chối.

    Trình duyệt luôn gửi Origin cho request ghi cross-origin; request không có Origin (curl, script) vẫn qua
    vì không phải CSRF từ trình duyệt.
    """
    origin = request.headers.get("origin")
    if request.method in UNSAFE_METHODS and origin is not None and origin not in ALLOWED_ORIGINS:
        return JSONResponse(status_code=403, content={"detail": "Origin không được phép"})
    return await call_next(request)


# include_router: "gắn" toàn bộ route đã định nghĩa trong api/documents.py
# vào app chính - từ giờ POST /api/documents/upload sẽ hoạt động
app.include_router(documents_router)
app.include_router(formulas_router)
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}