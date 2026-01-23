"""
API 响应模型定义
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class UploadDocumentResponse(BaseModel):
    """导入响应模型"""

    success: bool
    message: str
    doc_id: Optional[str] = None
    chunks_count: int = 0
    file_name: str
    file_format: str
    strategy: str


class ChunkResponse(BaseModel):
    """Chunk 响应模型"""

    id: str
    content: str
    metadata: Dict[str, Any]


class ChunksListResponse(BaseModel):
    """Chunks 列表响应模型"""

    chunks: List[ChunkResponse]
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: int = 0


class DocumentInfo(BaseModel):
    """文档信息模型"""

    doc_id: str
    doc_title: str
    chunks_count: int
    content_types: Dict[str, int]
    source: Optional[str] = None


class DocumentsListResponse(BaseModel):
    """文档列表响应模型"""

    documents: List[DocumentInfo]
    total: int


class SearchRequest(BaseModel):
    """搜索请求模型"""

    query: str
    top_k: int = 10
    use_rerank: bool = False
    retrieve_k: Optional[int] = None


class SearchResult(BaseModel):
    """搜索结果模型"""

    id: str
    content: str
    metadata: Dict[str, Any]
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None


class SearchResponse(BaseModel):
    """搜索响应模型"""

    results: List[SearchResult]
    total: int
    query: str


class ChatRequest(BaseModel):
    """对话请求模型"""

    message: str
    top_k: int = 5
    use_rerank: bool = True
    conversation_history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """对话响应模型"""

    response: str
    sources: Optional[List[SearchResult]] = None
