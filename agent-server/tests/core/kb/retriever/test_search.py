"""
tests/core/kb/retriever/test_search.py

测试 retriever/__init__.py 中的 search() 混合检索管道。
所有外部依赖（vector_retriever、fts_retriever、rrf、ChromaDB、reranker）均通过 mock 隔离。
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# --------------------------------------------------------------------------- #
# 通用 mock 数据                                                                #
# --------------------------------------------------------------------------- #

MOCK_VECTOR = [
    ("id1", 0.1, {"standard_no": "GB-001"}),
    ("id2", 0.3, {"standard_no": "GB-001"}),
]
MOCK_BM25 = [("id1", 10.0), ("id2", 5.0)]
MOCK_RRF_RESULT = ["id1", "id2"]
MOCK_CHROMA_DATA = {
    "ids": ["id1", "id2"],
    "documents": ["内容1", "内容2"],
    "metadatas": [
        {
            "standard_no": "GB-001",
            "semantic_type": "scope",
            "section_path": "1|1.1",
            "raw_content": "原始1",
        },
        {
            "standard_no": "GB-001",
            "semantic_type": "scope",
            "section_path": "1|1.2",
            "raw_content": "原始2",
        },
    ],
}
MOCK_RERANK_RESULT = [(0, 0.9), (1, 0.7)]


def _make_mocks(
    vector_return=None,
    bm25_return=None,
    rrf_return=None,
    chroma_return=None,
    rerank_return=None,
):
    """构建一套完整的 mock 对象，允许按需覆盖。"""
    mock_collection = MagicMock()
    mock_collection.get.return_value = chroma_return if chroma_return is not None else MOCK_CHROMA_DATA

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = rerank_return if rerank_return is not None else MOCK_RERANK_RESULT

    return dict(
        vector_query=AsyncMock(return_value=vector_return if vector_return is not None else MOCK_VECTOR),
        fts_query=MagicMock(return_value=bm25_return if bm25_return is not None else MOCK_BM25),
        rrf_merge=MagicMock(return_value=rrf_return if rrf_return is not None else MOCK_RRF_RESULT),
        get_collection=MagicMock(return_value=mock_collection),
        get_reranker=MagicMock(return_value=mock_reranker),
        mock_collection=mock_collection,
        mock_reranker=mock_reranker,
    )


def _patch_all(mocks):
    """返回 contextmanager 列表（使用 ExitStack 或直接叠 with 语句）。"""
    return [
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ]


# --------------------------------------------------------------------------- #
# 测试用例                                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_search_normal():
    """正常流程端到端：验证返回正确的 SearchResult 列表。"""
    mocks = _make_mocks()

    with (
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ):
        from app.core.kb.retriever import search
        results = await search("查询文本", top_k=2)

    assert len(results) == 2
    assert results[0]["chunk_id"] == "id1"
    assert results[0]["score"] == pytest.approx(0.9)
    assert results[0]["content"] == "内容1"
    assert results[0]["raw_content"] == "原始1"
    assert results[0]["standard_no"] == "GB-001"
    assert results[0]["semantic_type"] == "scope"
    assert results[0]["section_path"] == "1|1.1"

    assert results[1]["chunk_id"] == "id2"
    assert results[1]["score"] == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_search_filters_passed_to_retrievers():
    """filters 参数正确透传到 vector_retriever 和 fts_retriever。"""
    mocks = _make_mocks()
    filters = {"standard_no": "GB-002", "semantic_type": "definition"}

    with (
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ):
        from app.core.kb.retriever import search
        await search("查询文本", filters=filters, top_k=2)

    # vector_retriever.query 收到了 filters
    mocks["vector_query"].assert_called_once_with("查询文本", top_k=20, filters=filters)
    # fts_retriever.query 收到了 filters
    mocks["fts_query"].assert_called_once_with("查询文本", top_k=20, filters=filters)


@pytest.mark.asyncio
async def test_search_top_k_controls_result_count():
    """top_k 控制最终返回的结果数量（由 reranker 截断）。"""
    # reranker 仅返回 1 条
    mocks = _make_mocks(rerank_return=[(0, 0.95)])

    with (
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ):
        from app.core.kb.retriever import search
        results = await search("查询文本", top_k=1)

    assert len(results) == 1
    # 验证 reranker.rerank 收到了 top_k=1
    mocks["mock_reranker"].rerank.assert_called_once()
    call_args = mocks["mock_reranker"].rerank.call_args
    assert call_args.args[2] == 1 or call_args.kwargs.get("top_k") == 1


@pytest.mark.asyncio
async def test_search_empty_when_rrf_returns_nothing():
    """当 RRF 融合结果为空时，search() 直接返回空列表，不报错。"""
    mocks = _make_mocks(rrf_return=[])

    with (
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ):
        from app.core.kb.retriever import search
        results = await search("查询文本", top_k=5)

    assert results == []
    # ChromaDB 和 reranker 不应被调用
    mocks["mock_collection"].get.assert_not_called()
    mocks["mock_reranker"].rerank.assert_not_called()


@pytest.mark.asyncio
async def test_search_empty_when_both_retrievers_return_nothing():
    """当两个 retriever 都返回空时，search() 返回空列表。"""
    mocks = _make_mocks(
        vector_return=[],
        bm25_return=[],
        rrf_return=[],
    )

    with (
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ):
        from app.core.kb.retriever import search
        results = await search("无效查询", top_k=5)

    assert results == []


@pytest.mark.asyncio
async def test_search_skips_missing_chroma_ids():
    """RRF 返回了某些 id，但 ChromaDB 里不存在时，这些 id 被安全跳过。"""
    # ChromaDB 只返回 id1，id2 不存在
    chroma_data_partial = {
        "ids": ["id1"],
        "documents": ["内容1"],
        "metadatas": [
            {
                "standard_no": "GB-001",
                "semantic_type": "scope",
                "section_path": "1|1.1",
                "raw_content": "原始1",
            }
        ],
    }
    mocks = _make_mocks(
        chroma_return=chroma_data_partial,
        rerank_return=[(0, 0.88)],
    )

    with (
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ):
        from app.core.kb.retriever import search
        results = await search("查询文本", top_k=5)

    assert len(results) == 1
    assert results[0]["chunk_id"] == "id1"
    assert results[0]["score"] == pytest.approx(0.88)


@pytest.mark.asyncio
async def test_search_empty_when_all_chroma_ids_missing():
    """当 ChromaDB 返回空（所有 id 都不存在）时，search() 返回空列表。"""
    chroma_data_empty = {
        "ids": [],
        "documents": [],
        "metadatas": [],
    }
    mocks = _make_mocks(chroma_return=chroma_data_empty)

    with (
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ):
        from app.core.kb.retriever import search
        results = await search("查询文本", top_k=5)

    assert results == []
    # reranker 不应被调用
    mocks["mock_reranker"].rerank.assert_not_called()


@pytest.mark.asyncio
async def test_search_no_filters_passes_none():
    """不传 filters 时，两个 retriever 收到 filters=None。"""
    mocks = _make_mocks()

    with (
        patch("app.core.kb.retriever.vector_retriever.query", mocks["vector_query"]),
        patch("app.core.kb.retriever.fts_retriever.query", mocks["fts_query"]),
        patch("app.core.kb.retriever.rrf.merge", mocks["rrf_merge"]),
        patch("app.core.kb.retriever.get_collection", mocks["get_collection"]),
        patch("app.core.kb.retriever.get_reranker", mocks["get_reranker"]),
    ):
        from app.core.kb.retriever import search
        await search("查询文本")

    mocks["vector_query"].assert_called_once_with("查询文本", top_k=20, filters=None)
    mocks["fts_query"].assert_called_once_with("查询文本", top_k=20, filters=None)
