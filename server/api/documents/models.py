from typing import Optional

from pydantic import BaseModel


class DocumentInfo(BaseModel):
    doc_id: str
    title: str = ""
    standard_no: str
    doc_type: str
    chunks_count: int


class DocumentsListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    standard_no: Optional[str] = None
    doc_type: Optional[str] = None


class DeleteDocumentResponse(BaseModel):
    doc_id: str
    errors: list[str]


class ClearDocumentsResponse(BaseModel):
    status: str
    deleted_documents: int
    deleted_chunks: int

