from unittest.mock import AsyncMock, MagicMock, patch
import pytest


def _make_chunk(chunk_id="c1", content="文本", semantic_type="scope", section_path=None, raw_content="原始"):
    return {
        "chunk_id": chunk_id,
        "content": content,
        "semantic_type": semantic_type,
        "section_path": section_path or ["1", "1.1"],
        "raw_content": raw_content,
        "doc_metadata": {},
        "meta": {},
    }


def _make_doc_metadata(standard_no="GB/T-001", doc_type="additive"):
    return {"standard_no": standard_no, "doc_type": doc_type}


# ── delete_by_standard_no ──────────────────────────────────────────────

async def test_delete_by_standard_no_returns_true_on_success():
    """成功删除时返回 True，errors 不变"""
    mock_col = MagicMock()
    errors = []

    with patch("app.core.kb.writer.chroma_writer.get_collection", return_value=mock_col):
        from app.core.kb.writer.chroma_writer import delete_by_standard_no
        result = await delete_by_standard_no("GB/T-001", errors)

    assert result is True
    assert errors == []
    mock_col.delete.assert_called_once_with(where={"standard_no": {"$eq": "GB/T-001"}})


async def test_delete_by_standard_no_returns_false_on_error():
    """删除抛出异常时返回 False，errors 包含错误信息"""
    mock_col = MagicMock()
    mock_col.delete.side_effect = Exception("connection refused")
    errors = []

    with patch("app.core.kb.writer.chroma_writer.get_collection", return_value=mock_col):
        from app.core.kb.writer.chroma_writer import delete_by_standard_no
        result = await delete_by_standard_no("GB/T-001", errors)

    assert result is False
    assert len(errors) == 1
    assert "connection refused" in errors[0]


# ── write ──────────────────────────────────────────────────────────────

async def test_write_calls_upsert_with_embeddings():
    """write 向量化后调用 collection.upsert，传入正确字段"""
    mock_col = MagicMock()
    chunks = [_make_chunk("id1", "内容A"), _make_chunk("id2", "内容B")]
    doc_metadata = _make_doc_metadata()
    fake_embeddings = [[0.1, 0.2], [0.3, 0.4]]

    with patch("app.core.kb.writer.chroma_writer.get_collection", return_value=mock_col), \
         patch("app.core.kb.writer.chroma_writer.embed_batch", AsyncMock(return_value=fake_embeddings)):
        from app.core.kb.writer.chroma_writer import write
        await write(chunks, doc_metadata)

    call_kwargs = mock_col.upsert.call_args.kwargs
    assert call_kwargs["ids"] == ["id1", "id2"]
    assert call_kwargs["documents"] == ["内容A", "内容B"]
    assert call_kwargs["embeddings"] == fake_embeddings
    assert call_kwargs["metadatas"][0]["standard_no"] == "GB/T-001"
    assert call_kwargs["metadatas"][0]["semantic_type"] == "scope"
    assert call_kwargs["metadatas"][0]["section_path"] == "1|1.1"
    assert call_kwargs["metadatas"][0]["doc_type"] == "additive"
    assert call_kwargs["metadatas"][0]["raw_content"] == "原始"


async def test_write_section_path_serialized_with_pipe():
    """section_path 按 '|' 序列化写入 metadata"""
    mock_col = MagicMock()
    chunk = _make_chunk(section_path=["3", "3.1", "3.1.2"])

    with patch("app.core.kb.writer.chroma_writer.get_collection", return_value=mock_col), \
         patch("app.core.kb.writer.chroma_writer.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.writer.chroma_writer import write
        await write([chunk], _make_doc_metadata())

    meta = mock_col.upsert.call_args.kwargs["metadatas"][0]
    assert meta["section_path"] == "3|3.1|3.1.2"


async def test_write_empty_chunks_is_noop():
    """write 传入空列表时不调用 upsert"""
    mock_col = MagicMock()

    with patch("app.core.kb.writer.chroma_writer.get_collection", return_value=mock_col), \
         patch("app.core.kb.writer.chroma_writer.embed_batch", AsyncMock(return_value=[])):
        from app.core.kb.writer.chroma_writer import write
        await write([], _make_doc_metadata())

    mock_col.upsert.assert_not_called()


async def test_write_raw_content_truncated_when_over_2000():
    """raw_content 超过 2000 字符时截断，最终结果恰好为 2000 字符"""
    mock_col = MagicMock()
    long_raw = "x" * 2001
    chunk = _make_chunk(raw_content=long_raw)

    with patch("app.core.kb.writer.chroma_writer.get_collection", return_value=mock_col), \
         patch("app.core.kb.writer.chroma_writer.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.writer.chroma_writer import write
        await write([chunk], _make_doc_metadata())

    meta = mock_col.upsert.call_args.kwargs["metadatas"][0]
    suffix = "...（内容已截断）"
    assert meta["raw_content"].endswith(suffix)
    assert len(meta["raw_content"]) == 2000


async def test_write_raw_content_exactly_2000_not_truncated():
    """raw_content 恰好为 2000 字符时不截断，原样写入"""
    mock_col = MagicMock()
    exact_raw = "y" * 2000
    chunk = _make_chunk(raw_content=exact_raw)

    with patch("app.core.kb.writer.chroma_writer.get_collection", return_value=mock_col), \
         patch("app.core.kb.writer.chroma_writer.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.writer.chroma_writer import write
        await write([chunk], _make_doc_metadata())

    meta = mock_col.upsert.call_args.kwargs["metadatas"][0]
    assert meta["raw_content"] == exact_raw
    assert len(meta["raw_content"]) == 2000


async def test_write_raw_content_preserved_when_under_2000():
    """raw_content 不足 2000 字符时原样写入"""
    mock_col = MagicMock()
    short_raw = "短内容" * 100  # 300 字符
    chunk = _make_chunk(raw_content=short_raw)

    with patch("app.core.kb.writer.chroma_writer.get_collection", return_value=mock_col), \
         patch("app.core.kb.writer.chroma_writer.embed_batch", AsyncMock(return_value=[[0.1]])):
        from app.core.kb.writer.chroma_writer import write
        await write([chunk], _make_doc_metadata())

    meta = mock_col.upsert.call_args.kwargs["metadatas"][0]
    assert meta["raw_content"] == short_raw
