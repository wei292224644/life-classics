from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.documents.models import DocumentsListResponse, DocumentInfo, UploadDocumentResponse
from app.api.documents.service import DocumentsService

router = APIRouter()


@router.get("", response_model=DocumentsListResponse)
def list_documents():
    docs = DocumentsService.get_all_documents()
    return DocumentsListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total=len(docs),
    )


@router.post("", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    strategy: str = Form("text"),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
):
    try:
        content = await file.read()
        result = await DocumentsService.upload_document(
            file_content=content,
            filename=file.filename or "unknown",
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return UploadDocumentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    try:
        return DocumentsService.delete_document(doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
