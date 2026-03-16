from unittest.mock import AsyncMock, patch
import pytest

from app.core.parser_workflow.models import DocumentChunk


def _make_parser_result(standard_no="GB/T-001", chunks=None, errors=None):
    return {
        "chunks": chunks or [],
        "doc_metadata": {"standard_no": standard_no, "doc_type": "additive"},
        "errors": errors or [],
        "stats": {},
    }


# ── 正常路径 ────────────────────────────────────────────────────────────

async def test_write_to_kb_success_returns_ok_result():
    """正常写入时 chroma_ok=True, neo4j_ok=True, errors 为空"""
    result = _make_parser_result(chunks=[{"chunk_id": "c1", "content": "x",
                                           "content_type": "scope", "section_path": ["1"],
                                           "raw_content": "raw", "doc_metadata": {}, "meta": {}}])

    with patch("app.core.kb.writer.chroma_writer.delete_by_standard_no", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.neo4j_writer.delete_by_standard_no", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock()), \
         patch("app.core.kb.writer.neo4j_writer.write", AsyncMock()):
        from app.core.kb.writer import write_to_kb
        wr = await write_to_kb(result)

    assert wr["standard_no"] == "GB/T-001"
    assert wr["chunks_written"] == 1
    assert wr["chroma_ok"] is True
    assert wr["neo4j_ok"] is True
    assert wr["errors"] == []


async def test_write_to_kb_calls_delete_before_write():
    """delete 先于 write 调用（顺序验证）"""
    call_order = []

    async def mock_chroma_delete(sn, errors): call_order.append("chroma_delete"); return True
    async def mock_neo4j_delete(sn, errors): call_order.append("neo4j_delete"); return True
    async def mock_chroma_write(chunks, meta): call_order.append("chroma_write")
    async def mock_neo4j_write(chunks, meta): call_order.append("neo4j_write")

    with patch("app.core.kb.writer.chroma_writer.delete_by_standard_no", mock_chroma_delete), \
         patch("app.core.kb.writer.neo4j_writer.delete_by_standard_no", mock_neo4j_delete), \
         patch("app.core.kb.writer.chroma_writer.write", mock_chroma_write), \
         patch("app.core.kb.writer.neo4j_writer.write", mock_neo4j_write):
        from app.core.kb.writer import write_to_kb
        await write_to_kb(_make_parser_result())

    assert call_order.index("chroma_delete") < call_order.index("chroma_write")
    assert call_order.index("neo4j_delete") < call_order.index("neo4j_write")


# ── standard_no 缺失 ────────────────────────────────────────────────────

async def test_write_to_kb_missing_standard_no():
    """standard_no 缺失时直接返回 error WriteResult，不调用任何 writer"""
    result = {"chunks": [], "doc_metadata": {}, "errors": [], "stats": {}}

    with patch("app.core.kb.writer.chroma_writer.delete_by_standard_no") as mock_cd, \
         patch("app.core.kb.writer.neo4j_writer.delete_by_standard_no") as mock_nd:
        from app.core.kb.writer import write_to_kb
        wr = await write_to_kb(result)

    assert wr["chroma_ok"] is False
    assert wr["neo4j_ok"] is False
    assert len(wr["errors"]) == 1
    assert "standard_no missing" in wr["errors"][0]
    mock_cd.assert_not_called()
    mock_nd.assert_not_called()


# ── 单侧删除失败 ──────────────────────────────────────────────────────

async def test_chroma_delete_failure_skips_chroma_write():
    """ChromaDB 删除失败时跳过 ChromaDB 写入，Neo4j 正常写入"""
    with patch("app.core.kb.writer.chroma_writer.delete_by_standard_no", AsyncMock(return_value=False)), \
         patch("app.core.kb.writer.neo4j_writer.delete_by_standard_no", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock()) as mock_cw, \
         patch("app.core.kb.writer.neo4j_writer.write", AsyncMock()) as mock_nw:
        from app.core.kb.writer import write_to_kb
        wr = await write_to_kb(_make_parser_result())

    assert wr["chroma_ok"] is False
    assert wr["neo4j_ok"] is True
    mock_cw.assert_not_called()
    mock_nw.assert_called_once()


async def test_neo4j_delete_failure_skips_neo4j_write():
    """Neo4j 删除失败时跳过 Neo4j 写入，ChromaDB 正常写入"""
    with patch("app.core.kb.writer.chroma_writer.delete_by_standard_no", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.neo4j_writer.delete_by_standard_no", AsyncMock(return_value=False)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock()) as mock_cw, \
         patch("app.core.kb.writer.neo4j_writer.write", AsyncMock()) as mock_nw:
        from app.core.kb.writer import write_to_kb
        wr = await write_to_kb(_make_parser_result())

    assert wr["chroma_ok"] is True
    assert wr["neo4j_ok"] is False
    mock_cw.assert_called_once()
    mock_nw.assert_not_called()


# ── 单侧写入失败 ──────────────────────────────────────────────────────

async def test_chroma_write_failure_sets_chroma_ok_false():
    """ChromaDB 写入异常时 chroma_ok=False，errors 包含错误，neo4j_ok 不受影响"""
    with patch("app.core.kb.writer.chroma_writer.delete_by_standard_no", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.neo4j_writer.delete_by_standard_no", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock(side_effect=Exception("chroma timeout"))), \
         patch("app.core.kb.writer.neo4j_writer.write", AsyncMock()):
        from app.core.kb.writer import write_to_kb
        wr = await write_to_kb(_make_parser_result())

    assert wr["chroma_ok"] is False
    assert wr["neo4j_ok"] is True
    assert any("chroma timeout" in e for e in wr["errors"])


async def test_neo4j_write_failure_sets_neo4j_ok_false():
    """Neo4j 写入异常时 neo4j_ok=False，errors 包含错误，chroma_ok 不受影响"""
    with patch("app.core.kb.writer.chroma_writer.delete_by_standard_no", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.neo4j_writer.delete_by_standard_no", AsyncMock(return_value=True)), \
         patch("app.core.kb.writer.chroma_writer.write", AsyncMock()), \
         patch("app.core.kb.writer.neo4j_writer.write", AsyncMock(side_effect=Exception("neo4j timeout"))):
        from app.core.kb.writer import write_to_kb
        wr = await write_to_kb(_make_parser_result())

    assert wr["chroma_ok"] is True
    assert wr["neo4j_ok"] is False
    assert any("neo4j timeout" in e for e in wr["errors"])
