import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.search.models import (
    ChatRequest, ChatResponse,
    SearchRequest, SearchResponse, SearchResult,
)
from app.api.search.service import ChatService, SearchService

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
