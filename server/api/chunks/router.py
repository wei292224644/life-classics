from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.chunks.models import ChunksListResponse, ChunkResponse, UpdateChunkRequest
from api.chunks.service import ChunksService
from api.shared import safe_http_exception
from services.kb_service import KBService
from services.parser_workflow_service import ParserWorkflowService

router = APIRouter()


def get_kb_service() -> KBService:
    return KBService()


def get_parser_workflow_service() -> ParserWorkflowService:
    return ParserWorkflowService()


def get_chunks_service() -> ChunksService:
    kb_svc = get_kb_service()
    pw_svc = get_parser_workflow_service()
    return ChunksService(kb_service=kb_svc, parser_workflow_service=pw_svc)


@router.get("", response_model=ChunksListResponse)
async def list_chunks(
    doc_id: Optional[str] = Query(None),
    semantic_type: Optional[str] = Query(None),
    section_path: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    svc: ChunksService = Depends(get_chunks_service),
):
    chunks, total = await svc.get_chunks(
        doc_id=doc_id,
        semantic_type=semantic_type,
        section_path=section_path,
        limit=limit,
        offset=offset,
    )
    return ChunksListResponse(
        chunks=[ChunkResponse(**c) for c in chunks],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(chunks) < total,
    )


@router.get("/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(
    chunk_id: str,
    svc: ChunksService = Depends(get_chunks_service),
):
    chunk = await svc.get_chunk_by_id(chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="chunk not found")
    return ChunkResponse(**chunk)


@router.put("/{chunk_id}", response_model=ChunkResponse)
async def update_chunk(
    chunk_id: str,
    body: UpdateChunkRequest,
    svc: ChunksService = Depends(get_chunks_service),
):
    try:
        result = await svc.update_chunk(
            chunk_id=chunk_id,
            content=body.content,
            semantic_type=body.semantic_type,
            section_path=body.section_path,
        )
        return ChunkResponse(**result)
    except ValueError as exc:
        safe_http_exception(404, "CHUNK_NOT_FOUND", str(exc), exc=exc)
    except Exception as exc:
        safe_http_exception(500, "CHUNK_UPDATE_FAILED", "Failed to update chunk", exc=exc)


@router.delete("/{chunk_id}", status_code=204)
async def delete_chunk(
    chunk_id: str,
    svc: ChunksService = Depends(get_chunks_service),
):
    try:
        await svc.delete_chunk(chunk_id)
    except Exception as exc:
        safe_http_exception(500, "CHUNK_DELETE_FAILED", "Failed to delete chunk", exc=exc)


@router.post("/{chunk_id}/reparse", response_model=ChunkResponse)
async def reparse_chunk(
    chunk_id: str,
    svc: ChunksService = Depends(get_chunks_service),
):
    try:
        result = await svc.reparse_chunk(chunk_id)
        return ChunkResponse(**result)
    except ValueError as exc:
        safe_http_exception(404, "CHUNK_NOT_FOUND", str(exc), exc=exc)
    except Exception as exc:
        safe_http_exception(500, "CHUNK_REPARSE_FAILED", "Failed to reparse chunk", exc=exc)
