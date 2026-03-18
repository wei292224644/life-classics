"""
检索管道顶层入口。

组装 vector_retriever、fts_retriever、rrf、reranker 四个组件，
暴露统一的 search() 异步接口。
"""
from __future__ import annotations

import asyncio
from typing import List, TypedDict

from app.core.kb.retriever import fts_retriever, rrf, vector_retriever
from app.core.kb.writer.chroma_writer import get_collection
from app.core.kb.vector_store.rerank import get_reranker


class SearchResult(TypedDict):
    chunk_id: str
    standard_no: str
    semantic_type: str
    section_path: str
    content: str        # LLM 转写文本（ChromaDB documents 字段）
    raw_content: str    # 原始文本（来自 ChromaDB metadata["raw_content"]）
    score: float        # reranker 相关性分数


async def search(
    query: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> List[SearchResult]:
    """混合检索（向量 + BM25）并经 reranker 重排序后返回结果。

    Args:
        query: 查询文本
        filters: 过滤条件，如 {"standard_no": "GB 2762-2022"}
        top_k: 最终返回条数

    Returns:
        按 reranker 分数降序排列的 SearchResult 列表
    """
    # 1. 并行检索
    vector_results, bm25_results = await asyncio.gather(
        vector_retriever.query(query, top_k=20, filters=filters),
        asyncio.to_thread(fts_retriever.query, query, top_k=20, filters=filters),
    )

    # 2. RRF 融合
    chunk_ids = rrf.merge(
        [(cid, dist) for cid, dist, _ in vector_results],
        bm25_results,
        max_results=40,
    )

    if not chunk_ids:
        return []

    # 3. 批量从 ChromaDB 取回数据
    collection = get_collection()
    chroma_data = await asyncio.to_thread(
        collection.get,
        ids=chunk_ids,
        include=["documents", "metadatas"],
    )

    # 4. 建 id→data 映射
    id_to_data = {
        cid: (doc, meta)
        for cid, doc, meta in zip(
            chroma_data["ids"],
            chroma_data["documents"],
            chroma_data["metadatas"],
        )
    }

    # 5. 按 RRF 顺序提取，过滤掉 ChromaDB 里已不存在的 id
    ordered_chunks = [(cid, *id_to_data[cid]) for cid in chunk_ids if cid in id_to_data]

    if not ordered_chunks:
        return []

    documents = [chunk[1] for chunk in ordered_chunks]  # content 字符串列表

    # 6. Rerank（同步且 CPU/GPU 密集，用 to_thread 包装）
    reranker = get_reranker()
    ranked = await asyncio.to_thread(reranker.rerank, query, documents, top_k)

    # 7. 构造 SearchResult
    results: List[SearchResult] = []
    for original_idx, score in ranked:
        chunk_id, content, meta = ordered_chunks[original_idx]
        results.append(
            SearchResult(
                chunk_id=chunk_id,
                standard_no=meta.get("standard_no", ""),
                semantic_type=meta.get("semantic_type", ""),
                section_path=meta.get("section_path", ""),
                content=content,
                raw_content=meta.get("raw_content", ""),
                score=score,
            )
        )
    return results
