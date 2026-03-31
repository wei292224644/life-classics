from __future__ import annotations

from typing import List, TypedDict


class DocumentChunk(TypedDict):
    """
    Knowledge Base 写入/检索的“最终 chunk”数据结构。

    该类型用于 ChromaDB（向量 + documents + metadatas）与
    FTS5（tokenized_content）之间的统一数据契约。
    """

    chunk_id: str
    doc_metadata: dict
    section_path: List[str]
    structure_type: str
    semantic_type: str
    content: str
    raw_content: str
    meta: dict

