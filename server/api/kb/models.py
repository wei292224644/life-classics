from pydantic import BaseModel


class KBStatsResponse(BaseModel):
    total_chunks: int
    total_documents: int
    semantic_types: dict[str, int]
