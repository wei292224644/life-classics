from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.chunks.models import ChunksListResponse, ChunkResponse, UpdateChunkRequest
from api.chunks.service import ChunksService

router = APIRouter()


@router.get("", response_model=ChunksListResponse)
def list_chunks(
    doc_id: Optional[str] = Query(None),
    semantic_type: Optional[str] = Query(None),
    section_path: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    chunks, total = ChunksService.get_chunks(
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
    )


@router.get("/{chunk_id}", response_model=ChunkResponse)
def get_chunk(chunk_id: str):
    chunk = ChunksService.get_chunk_by_id(chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="chunk not found")
    return ChunkResponse(**chunk)


@router.put("/{chunk_id}", response_model=ChunkResponse)
async def update_chunk(chunk_id: str, body: UpdateChunkRequest):
    try:
        result = await ChunksService.update_chunk(
            chunk_id=chunk_id,
            content=body.content,
            semantic_type=body.semantic_type,
            section_path=body.section_path,
        )
        return ChunkResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chunk_id}", status_code=204)
def delete_chunk(chunk_id: str):
    try:
        ChunksService.delete_chunk(chunk_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
