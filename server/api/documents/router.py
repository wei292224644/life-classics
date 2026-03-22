from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from api.documents.models import DocumentsListResponse, DocumentInfo, UpdateDocumentRequest
from api.documents.service import DocumentsService

router = APIRouter()


@router.get("", response_model=DocumentsListResponse)
def list_documents():
    docs = DocumentsService.get_all_documents()
    return DocumentsListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total=len(docs),
    )


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
):
    content = await file.read()
    return StreamingResponse(
        DocumentsService.upload_document_stream(
            file_content=content,
            filename=file.filename or "unknown",
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/clear")
def clear_all_documents():
    try:
        return DocumentsService.clear_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    try:
        return DocumentsService.delete_document(doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{doc_id}", response_model=DocumentInfo)
def update_document(doc_id: str, body: UpdateDocumentRequest):
    try:
        result = DocumentsService.update_document(
            doc_id,
            body.model_dump(exclude_none=True),
        )
        return DocumentInfo(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
