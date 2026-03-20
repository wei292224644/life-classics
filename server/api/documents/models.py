from pydantic import BaseModel


class DocumentInfo(BaseModel):
    doc_id: str
    standard_no: str
    doc_type: str
    chunks_count: int


class DocumentsListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


