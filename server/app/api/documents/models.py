from typing import Optional
from pydantic import BaseModel


class DocumentInfo(BaseModel):
    doc_id: str
    standard_no: str
    doc_type: str
    chunks_count: int


class DocumentsListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


class UploadDocumentResponse(BaseModel):
    success: bool
    message: str
    doc_id: Optional[str] = None
    chunks_count: int = 0
    file_name: str
    strategy: str
