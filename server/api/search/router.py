import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.search.models import (
    ChatRequest, ChatResponse,
    SearchRequest, SearchResponse, SearchResult,
    SearchResultItem,
)
from api.search.service import ChatService, SearchService, UnifiedSearchService
from api.shared import Paginated
from database.session import get_async_session
from db_repositories.search import SearchRepository

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        results = await SearchService.search(
            query=request.query,
            top_k=request.top_k,
            use_rerank=request.use_rerank,
            retrieve_k=request.retrieve_k,
        )
        return SearchResponse(results=results, total=len(results), query=request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response, sources = await ChatService.chat(request)
        return ChatResponse(response=response, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream/start")
def start_chat_stream(request: ChatRequest):
    session_id = ChatService.start_chat_stream(request)
    return {"session_id": session_id}


@router.get("/chat/stream/{session_id}")
async def chat_stream(session_id: str):
    return StreamingResponse(
        ChatService.chat_stream_generator(session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


def _get_search_repository(
    session: AsyncSession = Depends(get_async_session),
) -> SearchRepository:
    return SearchRepository(session)


def _get_unified_search_service(
    repo: SearchRepository = Depends(_get_search_repository),
) -> UnifiedSearchService:
    return UnifiedSearchService(repo)


@router.get("/search", response_model=Paginated[SearchResultItem], tags=["Search"])
async def unified_search(
    q: str = Query(..., min_length=1, max_length=100),
    result_type: Literal["all", "product", "ingredient"] = Query(default="all", alias="type"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    svc: UnifiedSearchService = Depends(_get_unified_search_service),
):
    """按关键词搜索食品和配料，支持分页。type 参数过滤结果类型。"""
    if not q.strip():
        raise HTTPException(status_code=400, detail="q must not be blank")
    return await svc.search(q=q.strip(), result_type=result_type, offset=offset, limit=limit)
