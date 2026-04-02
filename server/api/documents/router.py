from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from api.documents.models import DocumentsListResponse, DocumentInfo, UpdateDocumentRequest, DeleteDocumentResponse, ClearDocumentsResponse
from api.documents.service import DocumentsService
from api.shared import safe_http_exception
from services.kb_service import KBService
from services.parser_workflow_service import ParserWorkflowService

router = APIRouter()


def get_kb_service() -> KBService:
    return KBService()


def get_parser_workflow_service() -> ParserWorkflowService:
    return ParserWorkflowService()


def get_documents_service(
    kb_svc: KBService = Depends(get_kb_service),
    parser_svc: ParserWorkflowService = Depends(get_parser_workflow_service),
) -> DocumentsService:
    return DocumentsService(kb_svc, parser_svc)


@router.get("", response_model=DocumentsListResponse)
async def list_documents(svc: DocumentsService = Depends(get_documents_service)):
    docs = svc.get_all_documents()
    return DocumentsListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total=len(docs),
    )


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    svc: DocumentsService = Depends(get_documents_service),
):
    content = await file.read()
    return StreamingResponse(
        svc.upload_document_stream(
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


@router.delete("/clear", response_model=ClearDocumentsResponse)
async def clear_all_documents(svc: DocumentsService = Depends(get_documents_service)):
    try:
        return await svc.clear_all()
    except Exception as exc:
        safe_http_exception(500, "CLEAR_DOCUMENTS_FAILED", "Failed to clear documents", exc=exc)


@router.delete("/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(doc_id: str, svc: DocumentsService = Depends(get_documents_service)):
    try:
        return await svc.delete_document(doc_id)
    except ValueError as exc:
        safe_http_exception(404, "DOCUMENT_NOT_FOUND", str(exc), exc=exc)
    except Exception as exc:
        safe_http_exception(500, "DELETE_DOCUMENT_FAILED", "Failed to delete document", exc=exc)


@router.patch("/{doc_id}", response_model=DocumentInfo)
async def update_document(
    doc_id: str,
    body: UpdateDocumentRequest,
    svc: DocumentsService = Depends(get_documents_service),
):
    try:
        result = await svc.update_document(doc_id, body.model_dump(exclude_none=True))
        return DocumentInfo(**result)
    except ValueError as exc:
        safe_http_exception(404, "DOCUMENT_NOT_FOUND", str(exc), exc=exc)
    except Exception as exc:
        safe_http_exception(500, "UPDATE_DOCUMENT_FAILED", "Failed to update document", exc=exc)
