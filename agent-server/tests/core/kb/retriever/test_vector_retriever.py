from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest


def _make_chroma_result(ids, distances, metadatas):
    """构造 ChromaDB collection.query() 返回格式。"""
    return {
        "ids": [ids],
        "distances": [distances],
        "metadatas": [metadatas],
    }


# ── query 基本功能 ──────────────────────────────────────────────────────

async def test_query_returns_top_k_results():
    """正常查询返回不超过 top_k 条结果，格式为 (chunk_id, distance, metadata)"""
    ids = [f"id{i}" for i in range(5)]
    distances = [0.1 * i for i in range(5)]
    metadatas = [{"standard_no": f"GB-{i}"} for i in range(5)]

    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result(ids, distances, metadatas)
    fake_embedding = [0.1, 0.2, 0.3]

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", AsyncMock(return_value=[fake_embedding])):
        from app.core.kb.retriever.vector_retriever import query
        results = await query("查询文本", top_k=5)

    assert len(results) == 5
    assert results[0] == ("id0", 0.0, {"standard_no": "GB-0"})
    assert results[4] == ("id4", 0.4, {"standard_no": "GB-4"})


async def test_query_calls_embed_batch_with_query_text():
    """embed_batch 以查询文本调用"""
    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result(["id1"], [0.1], [{"k": "v"}])
    fake_embed = AsyncMock(return_value=[[0.5, 0.6]])

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", fake_embed):
        from app.core.kb.retriever.vector_retriever import query
        await query("测试查询")

    fake_embed.assert_called_once_with(["测试查询"])


async def test_query_passes_embedding_to_collection():
    """collection.query 使用 embed_batch 返回的向量"""
    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result(["id1"], [0.2], [{}])
    expected_embedding = [1.0, 2.0, 3.0]

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", AsyncMock(return_value=[expected_embedding])):
        from app.core.kb.retriever.vector_retriever import query
        await query("文本", top_k=10)

    call_kwargs = mock_col.query.call_args.kwargs
    assert call_kwargs["query_embeddings"] == [expected_embedding]
    assert call_kwargs["n_results"] == 10


# ── filters 过滤 ───────────────────────────────────────────────────────

async def test_query_no_filters_no_where_param():
    """不传 filters 时，collection.query 不带 where 参数"""
    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result([], [], [])

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.retriever.vector_retriever import query
        await query("文本")

    call_kwargs = mock_col.query.call_args.kwargs
    assert "where" not in call_kwargs


async def test_query_single_filter_converted_to_chroma_format():
    """单字段 filters 转换为 {key: {"$eq": value}} 格式"""
    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result(["id1"], [0.1], [{"standard_no": "GB 2762-2022"}])

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.retriever.vector_retriever import query
        results = await query("文本", filters={"standard_no": "GB 2762-2022"})

    call_kwargs = mock_col.query.call_args.kwargs
    assert call_kwargs["where"] == {"standard_no": {"$eq": "GB 2762-2022"}}
    assert len(results) == 1


async def test_query_multi_filter_uses_and_operator():
    """多字段 filters 转换为 {"$and": [...]} 格式"""
    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result([], [], [])

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.retriever.vector_retriever import query
        await query("文本", filters={"standard_no": "GB 2762-2022", "doc_type": "additive"})

    call_kwargs = mock_col.query.call_args.kwargs
    where = call_kwargs["where"]
    assert "$and" in where
    assert {"standard_no": {"$eq": "GB 2762-2022"}} in where["$and"]
    assert {"doc_type": {"$eq": "additive"}} in where["$and"]


async def test_query_filters_none_no_where_param():
    """filters=None 时不传 where 参数"""
    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result([], [], [])

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.retriever.vector_retriever import query
        await query("文本", filters=None)

    call_kwargs = mock_col.query.call_args.kwargs
    assert "where" not in call_kwargs


# ── 空结果 ─────────────────────────────────────────────────────────────

async def test_query_empty_collection_returns_empty_list():
    """空 collection 返回空列表，不报错"""
    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result([], [], [])

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.retriever.vector_retriever import query
        results = await query("文本", top_k=20)

    assert results == []


async def test_query_fewer_results_than_top_k():
    """实际结果少于 top_k 时正常返回（不补全）"""
    mock_col = MagicMock()
    mock_col.query.return_value = _make_chroma_result(["id1", "id2"], [0.1, 0.2], [{}, {}])

    with patch("app.core.kb.retriever.vector_retriever.get_collection", return_value=mock_col), \
         patch("app.core.kb.retriever.vector_retriever.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.retriever.vector_retriever import query
        results = await query("文本", top_k=20)

    assert len(results) == 2


# ── _to_chroma_where 单元测试 ──────────────────────────────────────────

def test_to_chroma_where_single_field():
    """单字段直接返回 {key: {"$eq": value}}"""
    from app.core.kb.retriever.vector_retriever import _to_chroma_where
    result = _to_chroma_where({"standard_no": "GB 2762"})
    assert result == {"standard_no": {"$eq": "GB 2762"}}


def test_to_chroma_where_multiple_fields():
    """多字段返回 {"$and": [...]}"""
    from app.core.kb.retriever.vector_retriever import _to_chroma_where
    result = _to_chroma_where({"standard_no": "GB 2762", "doc_type": "additive"})
    assert result == {
        "$and": [
            {"standard_no": {"$eq": "GB 2762"}},
            {"doc_type": {"$eq": "additive"}},
        ]
    }
