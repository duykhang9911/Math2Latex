import uuid
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str

    class Config:
        from_attributes = True