from __future__ import annotations

import asyncio
from typing import List

from kb.embeddings import embed_batch
from kb.writer.chroma_writer import get_collection


def _to_chroma_where(filters: dict) -> dict:
    """将普通 dict 过滤条件转换为 ChromaDB where 格式。"""
    items = [{k: {"$eq": v}} for k, v in filters.items()]
    if len(items) == 1:
        return items[0]
    return {"$and": items}


async def query(
    query_text: str,
    top_k: int = 20,
    filters: dict | None = None,
) -> List[tuple[str, float, dict]]:
    """查询 ChromaDB，返回 [(chunk_id, distance, metadata), ...]。

    Args:
        query_text: 查询文本
        top_k: 返回结果数量上限
        filters: 过滤条件，格式为普通 dict，如 {"standard_no": "GB 2762-2022"}
                 会自动转换为 ChromaDB where 格式

    Returns:
        按距离升序排列的 (chunk_id, distance, metadata) 列表，距离越小越相关
    """
    embeddings = await embed_batch([query_text])
    query_embedding = embeddings[0]

    collection = get_collection()

    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
    }
    if filters:
        kwargs["where"] = _to_chroma_where(filters)

    result = await asyncio.to_thread(collection.query, **kwargs)

    ids = result["ids"][0]
    distances = result["distances"][0]
    metadatas = result["metadatas"][0]

    return list(zip(ids, distances, metadatas))
