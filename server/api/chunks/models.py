from typing import Any, Optional
from pydantic import BaseModel


class ChunkResponse(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]


class ChunksListResponse(BaseModel):
    chunks: list[ChunkResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class UpdateChunkRequest(BaseModel):
    content: str
    semantic_type: str
    section_path: str  # "/" 分隔，如 "3/3.1"
