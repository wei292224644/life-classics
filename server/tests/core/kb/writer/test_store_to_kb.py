from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import kb.writer as writer_module
from parser.models import DocumentChunk, WorkflowState


@pytest.fixture(autouse=True)
def reset_db_initialized():
    """每个测试前重置 _db_initialized，避免懒初始化 flag 跨测试污染。"""
    writer_module._db_initialized = False
    yield
    writer_module._db_initialized = False


def _make_state(
    doc_id: str | None = "test-doc-uuid-1234",
    standard_no: str | None = "GB 1234-2020",
    chunks: list | None = None,
    errors: list | None = None,
) -> WorkflowState:
    """构造测试用 WorkflowState。"""
    if chunks is None:
        chunks = [
            DocumentChunk(
                chunk_id="abc123",
                doc_metadata={"doc_id": doc_id or "", "standard_no": standard_no or ""},
                section_path=["1"],
                structure_type="paragraph",
                semantic_type="scope",
                content="测试内容",
                raw_content="测试内容",
                meta={},
            )
        ]
    meta: dict = {}
    if doc_id:
        meta["doc_id"] = doc_id
    if standard_no:
        meta["standard_no"] = standard_no
    return WorkflowState(
        md_content="# test",
        doc_metadata=meta,
        config={},
        rules_dir="",
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=chunks,
        errors=errors or ["parse warning: something minor"],
    )


@pytest.mark.asyncio
async def test_missing_doc_id_returns_ok_false():
    """doc_id 缺失时返回 ok=False，chunks_written=0。"""
    state = _make_state(doc_id=None)

    with patch("app.core.kb.writer.fts_writer.init_db", MagicMock()), \
         patch("app.core.kb.writer.chroma_writer.delete_by_doc_id", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.fts_writer.delete_by_doc_id", MagicMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock()), \
         patch("app.core.kb.writer.fts_writer.write", MagicMock()):
        result = await writer_module.store_to_kb(state)

    assert result["ok"] is False
    assert result["chunks_written"] == 0
    assert result["doc_id"] == ""
    assert any("doc_id missing" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_normal_write_success():
    """正常流程：chunks_written == len(final_chunks)，ok=True。"""
    state = _make_state()

    with patch("app.core.kb.writer.fts_writer.init_db", MagicMock()), \
         patch("app.core.kb.writer.chroma_writer.delete_by_doc_id", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.fts_writer.delete_by_doc_id", MagicMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock()), \
         patch("app.core.kb.writer.fts_writer.write", MagicMock()):
        result = await writer_module.store_to_kb(state)

    assert result["ok"] is True
    assert result["chunks_written"] == len(state["final_chunks"])
    assert result["doc_id"] == "test-doc-uuid-1234"
    assert result["standard_no"] == "GB 1234-2020"
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_chroma_delete_failure_stops_write():
    """ChromaDB 删除失败时不执行写入，返回 ok=False。"""
    state = _make_state()
    chroma_write_mock = AsyncMock()
    fts_write_mock = MagicMock()

    with patch("app.core.kb.writer.fts_writer.init_db", MagicMock()), \
         patch("app.core.kb.writer.chroma_writer.delete_by_doc_id", AsyncMock(return_value=False)), \
         patch("app.core.kb.writer.fts_writer.delete_by_doc_id", MagicMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", chroma_write_mock), \
         patch("app.core.kb.writer.fts_writer.write", fts_write_mock):
        result = await writer_module.store_to_kb(state)

    assert result["ok"] is False
    chroma_write_mock.assert_not_called()
    fts_write_mock.assert_not_called()


@pytest.mark.asyncio
async def test_fts_delete_failure_stops_write():
    """SQLite FTS 删除失败时不执行写入，返回 ok=False。"""
    state = _make_state()
    chroma_write_mock = AsyncMock()
    fts_write_mock = MagicMock()

    with patch("app.core.kb.writer.fts_writer.init_db", MagicMock()), \
         patch("app.core.kb.writer.chroma_writer.delete_by_doc_id", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.fts_writer.delete_by_doc_id", MagicMock(return_value=False)), \
         patch("app.core.kb.writer.chroma_writer.write", chroma_write_mock), \
         patch("app.core.kb.writer.fts_writer.write", fts_write_mock):
        result = await writer_module.store_to_kb(state)

    assert result["ok"] is False
    chroma_write_mock.assert_not_called()
    fts_write_mock.assert_not_called()


@pytest.mark.asyncio
async def test_store_result_errors_do_not_include_state_errors():
    """StoreResult.errors 不包含 state["errors"] 中的 parse 阶段警告。"""
    parse_warning = "parse warning: something minor"
    state = _make_state(errors=[parse_warning])

    with patch("app.core.kb.writer.fts_writer.init_db", MagicMock()), \
         patch("app.core.kb.writer.chroma_writer.delete_by_doc_id", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.fts_writer.delete_by_doc_id", MagicMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock()), \
         patch("app.core.kb.writer.fts_writer.write", MagicMock()):
        result = await writer_module.store_to_kb(state)

    assert parse_warning not in result["errors"]


@pytest.mark.asyncio
async def test_chroma_write_failure_marks_ok_false():
    """ChromaDB 写入失败时 ok=False，且 errors 中包含 chroma 错误。"""
    state = _make_state()

    with patch("app.core.kb.writer.fts_writer.init_db", MagicMock()), \
         patch("app.core.kb.writer.chroma_writer.delete_by_doc_id", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.fts_writer.delete_by_doc_id", MagicMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock(side_effect=RuntimeError("chroma down"))), \
         patch("app.core.kb.writer.fts_writer.write", MagicMock()):
        result = await writer_module.store_to_kb(state)

    assert result["ok"] is False
    assert any("chroma write error" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_fts_write_failure_marks_ok_false():
    """FTS 写入失败时 ok=False，且 errors 中包含 fts 错误。"""
    state = _make_state()

    with patch("app.core.kb.writer.fts_writer.init_db", MagicMock()), \
         patch("app.core.kb.writer.chroma_writer.delete_by_doc_id", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.fts_writer.delete_by_doc_id", MagicMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock()), \
         patch("app.core.kb.writer.fts_writer.write", MagicMock(side_effect=RuntimeError("sqlite down"))):
        result = await writer_module.store_to_kb(state)

    assert result["ok"] is False
    assert any("fts write error" in e for e in result["errors"])
