import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str

    class Config:
        from_attributes = True


class DocumentSummary(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: str
    file_size_bytes: int | None
    page_count: int | None
    formula_count: int
    submitted_count: int
    created_at: datetime | None
    updated_at: datetime | None


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int
    limit: int
    offset: int
