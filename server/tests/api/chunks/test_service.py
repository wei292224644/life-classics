import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_col_result(ids=None, docs=None, metadatas=None):
    return {
        "ids": ids or [],
        "documents": docs or [],
        "metadatas": metadatas or [],
    }


def _meta(doc_id="d1", semantic_type="scope", section_path="1|1.1", standard_no="GB 2762", doc_type="food"):
    return {"doc_id": doc_id, "semantic_type": semantic_type, "section_path": section_path,
            "standard_no": standard_no, "doc_type": doc_type, "raw_content": "原始"}


def test_get_chunks_no_filter_returns_all():
    mock_col = MagicMock()
    mock_col.get.side_effect = [
        _make_col_result(["c1", "c2"], ["内容A", "内容B"], [_meta(), _meta("d2", "definition", "3|3.1")]),
        _make_col_result(["c1", "c2"]),  # count query
    ]

    with patch("api.chunks.service.get_collection", return_value=mock_col):
        from api.chunks.service import ChunksService
        chunks, total = ChunksService.get_chunks(limit=20, offset=0)

    assert len(chunks) == 2
    assert total == 2


def test_get_chunks_section_path_converted_to_pipe():
    """section_path 查询参数 '3/3.1' 转换为 ChromaDB '3|3.1'"""
    mock_col = MagicMock()
    mock_col.get.side_effect = [
        _make_col_result(["c1"], ["内容"], [_meta(section_path="3|3.1")]),
        _make_col_result(["c1"]),
    ]

    with patch("api.chunks.service.get_collection", return_value=mock_col):
        from api.chunks.service import ChunksService
        ChunksService.get_chunks(section_path="3/3.1", limit=20, offset=0)

    call_kwargs = mock_col.get.call_args_list[0].kwargs
    assert call_kwargs["where"]["section_path"]["$eq"] == "3|3.1"


def test_get_chunk_by_id_returns_chunk():
    mock_col = MagicMock()
    mock_col.get.return_value = _make_col_result(["c1"], ["内容"], [_meta()])

    with patch("api.chunks.service.get_collection", return_value=mock_col):
        from api.chunks.service import ChunksService
        chunk = ChunksService.get_chunk_by_id("c1")

    assert chunk is not None
    assert chunk["id"] == "c1"
    assert chunk["content"] == "内容"


def test_get_chunk_by_id_returns_none_if_not_found():
    mock_col = MagicMock()
    mock_col.get.return_value = _make_col_result([], [], [])

    with patch("api.chunks.service.get_collection", return_value=mock_col):
        from api.chunks.service import ChunksService
        chunk = ChunksService.get_chunk_by_id("nonexistent")

    assert chunk is None


@pytest.mark.asyncio
async def test_update_chunk_calls_reembed_and_upsert():
    """更新 chunk 时重新 embed 并 upsert 到 ChromaDB，同时更新 FTS"""
    mock_col = MagicMock()
    mock_col.get.return_value = _make_col_result(["c1"], ["旧内容"], [_meta()])
    fake_embedding = [[0.9, 0.8]]

    with patch("api.chunks.service.get_collection", return_value=mock_col), \
         patch("api.chunks.service.embed_batch", AsyncMock(return_value=fake_embedding)), \
         patch("api.chunks.service.fts_writer") as mock_fts:
        from api.chunks.service import ChunksService
        result = await ChunksService.update_chunk(
            chunk_id="c1",
            content="新内容",
            semantic_type="definition",
            section_path="2/2.1",
        )

    upsert_kwargs = mock_col.upsert.call_args.kwargs
    assert upsert_kwargs["ids"] == ["c1"]
    assert upsert_kwargs["documents"] == ["新内容"]
    assert upsert_kwargs["embeddings"] == fake_embedding
    assert upsert_kwargs["metadatas"][0]["semantic_type"] == "definition"
    assert upsert_kwargs["metadatas"][0]["section_path"] == "2|2.1"
    mock_fts.write.assert_called_once()
    assert result["id"] == "c1"


def test_delete_chunk_calls_chroma_and_fts():
    mock_col = MagicMock()
    mock_col.get.return_value = _make_col_result(["c1"], ["内容"], [_meta()])

    with patch("api.chunks.service.get_collection", return_value=mock_col), \
         patch("api.chunks.service.fts_writer") as mock_fts:
        from api.chunks.service import ChunksService
        ChunksService.delete_chunk("c1")

    mock_col.delete.assert_called_once_with(ids=["c1"])


@pytest.mark.asyncio
async def test_reparse_chunk_rebuilds_classified_and_reruns_transform():
    """reparse_chunk 重建 ClassifiedChunk，重跑 transform_node → merge_node，upsert 回 ChromaDB + FTS"""
    existing_meta = {
        "doc_id": "d1",
        "semantic_type": "scope",
        "section_path": "1|1.1",
        "standard_no": "GB 2762",
        "doc_type": "food",
        "raw_content": "原始markdown内容",
        "segment_raw_content": "分类后的段落原始文本",
        "structure_type": "paragraph",
        "transform_strategy": "nl",
        "prompt_template": "改写为自然语言",
        "cross_refs": ["表1"],
        "failed_table_refs": [],
    }

    mock_col = MagicMock()
    mock_col.get.return_value = _make_col_result(
        ["c1"],
        ["transform后的内容"],
        [existing_meta],
    )

    fake_embedding = [[0.1, 0.2]]
    mock_transform_result = {
        "final_chunks": [
            {
                "chunk_id": "new_c1_id",
                "doc_metadata": {"doc_id": "d1", "standard_no": "GB 2762", "doc_type": "food"},
                "section_path": ["1", "1.1"],
                "structure_type": "paragraph",
                "semantic_type": "scope",
                "content": "transform后的内容",
                "raw_content": "原始markdown内容",
                "meta": {
                    "transform_strategy": "nl",
                    "segment_raw_content": "分类后的段落原始文本",
                    "cross_refs": ["表1"],
                    "failed_table_refs": [],
                },
            }
        ],
        "errors": [],
    }
    mock_merge_result = {
        "final_chunks": mock_transform_result["final_chunks"],
        "doc_metadata": {"doc_id": "d1", "standard_no": "GB 2762", "doc_type": "food"},
    }

    with patch("api.chunks.service.get_collection", return_value=mock_col), \
         patch("api.chunks.service.embed_batch", AsyncMock(return_value=fake_embedding)), \
         patch("api.chunks.service.transform_node", AsyncMock(return_value=mock_transform_result)) as mock_transform, \
         patch("api.chunks.service.merge_node", return_value=mock_merge_result) as mock_merge, \
         patch("api.chunks.service.fts_writer") as mock_fts, \
         patch("api.chunks.service.settings") as mock_settings:
        mock_settings.CHROMA_PERSIST_DIR = "./db"
        from api.chunks.service import ChunksService
        result = await ChunksService.reparse_chunk("c1")

    # 验证 transform_node 被调用，且 classified_chunks 的 segment.content 等于 metadata["segment_raw_content"]
    transform_call_args = mock_transform.call_args[0][0]
    assert transform_call_args["classified_chunks"][0]["segments"][0]["content"] == existing_meta["segment_raw_content"]
    assert transform_call_args["classified_chunks"][0]["segments"][0]["confidence"] == 1.0
    assert transform_call_args["classified_chunks"][0]["segments"][0]["escalated"] is False

    # 验证 merge_node 被调用
    mock_merge.assert_called_once()

    # 验证 upsert 的 documents 为新内容
    upsert_kwargs = mock_col.upsert.call_args.kwargs
    assert upsert_kwargs["documents"] == [mock_transform_result["final_chunks"][0]["content"]]
    assert upsert_kwargs["metadatas"][0]["segment_raw_content"] == existing_meta["segment_raw_content"]

    # 验证 FTS write 被调用
    mock_fts.write.assert_called_once()

    # 验证 upsert 被调用
    mock_col.upsert.assert_called_once()

    # 验证返回的 metadata 字段
    assert result["metadata"]["semantic_type"] == "scope"
    assert result["metadata"]["section_path"] == "1|1.1"


@pytest.mark.asyncio
async def test_reparse_chunk_not_found():
    """chunk 不存在时抛出 ValueError(404)"""
    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": [], "documents": [], "metadatas": []}

    with patch("api.chunks.service.get_collection", return_value=mock_col):
        from api.chunks.service import ChunksService
        with pytest.raises(ValueError, match="not found"):
            await ChunksService.reparse_chunk("nonexistent")


@pytest.mark.asyncio
async def test_reparse_chunk_transform_returns_empty():
    """transform 产出为空时抛出 ValueError"""
    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["c1"],
        "documents": ["旧内容"],
        "metadatas": [{
            "doc_id": "d1", "semantic_type": "scope", "structure_type": "paragraph",
            "section_path": "1|1.1", "standard_no": "GB 2762", "doc_type": "food",
            "raw_content": "原始", "segment_raw_content": "seg原始",
            "transform_strategy": "plain_embed", "prompt_template": "",
            "cross_refs": [], "failed_table_refs": [],
        }],
    }

    async def mock_transform_fn(*args, **kwargs):
        return {"final_chunks": [], "errors": []}

    with patch("api.chunks.service.get_collection", return_value=mock_col), \
         patch("api.chunks.service.embed_batch", AsyncMock(return_value=[[0.1, 0.2]])), \
         patch("api.chunks.service.transform_node", new_callable=AsyncMock) as mock_transform, \
         patch("api.chunks.service.merge_node", return_value={"final_chunks": [], "doc_metadata": {}}), \
         patch("api.chunks.service.fts_writer") as mock_fts, \
         patch("api.chunks.service.settings") as mock_settings:
        mock_transform.side_effect = mock_transform_fn
        mock_settings.CHROMA_PERSIST_DIR = "./db"

        from api.chunks.service import ChunksService
        with pytest.raises(ValueError, match="produced no chunks"):
            await ChunksService.reparse_chunk("c1")
