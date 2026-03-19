from typing import Any, Optional
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    use_rerank: bool = False
    retrieve_k: Optional[int] = None


class SearchResult(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str


class ChatRequest(BaseModel):
    message: str
    top_k: int = 5
    use_rerank: bool = True
    conversation_history: Optional[list[dict[str, str]]] = None


class ChatResponse(BaseModel):
    response: str
    sources: Optional[list[SearchResult]] = None
