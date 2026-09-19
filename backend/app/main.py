from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router

app = FastAPI(title="Math2Latex API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include_router: "gắn" toàn bộ route đã định nghĩa trong api/documents.py
# vào app chính - từ giờ POST /api/documents/upload sẽ hoạt động
app.include_router(documents_router)


@app.get("/health")
def health():
    return {"status": "ok"}