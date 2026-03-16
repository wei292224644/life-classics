from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest


def _make_chunk(chunk_id="c1", content_type="scope", section_path=None, content="text", raw_content="raw"):
    return {
        "chunk_id": chunk_id,
        "content_type": content_type,
        "section_path": section_path or ["1"],
        "content": content,
        "raw_content": raw_content,
        "doc_metadata": {},
        "meta": {},
    }


def _make_doc_metadata(**kwargs):
    base = {
        "standard_no": "GB/T-001",
        "title": "测试标准",
        "doc_type": "additive",
        "doc_type_source": "rule",
        "publish_date": "2016-01-01",
        "implement_date": "2016-07-01",
        "status": "现行",
        "issuing_authority": "国家卫生健康委员会",
    }
    base.update(kwargs)
    return base


# ── delete_by_standard_no ──────────────────────────────────────────────

async def test_delete_by_standard_no_executes_cypher():
    """删除成功时执行正确的 Cypher 并返回 True"""
    mock_session = AsyncMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
    errors = []

    with patch("app.core.kb.writer.neo4j_writer.get_neo4j_driver", return_value=mock_driver):
        from app.core.kb.writer.neo4j_writer import delete_by_standard_no
        result = await delete_by_standard_no("GB/T-001", errors)

    assert result is True
    assert errors == []
    mock_session.run.assert_called_once()
    cypher = mock_session.run.call_args.args[0]
    assert "OPTIONAL MATCH" in cypher
    assert "DETACH DELETE" in cypher


async def test_delete_by_standard_no_returns_false_on_error():
    """删除抛出异常时返回 False，errors 包含错误信息"""
    mock_driver = MagicMock()
    mock_driver.session.side_effect = Exception("neo4j unreachable")
    errors = []

    with patch("app.core.kb.writer.neo4j_writer.get_neo4j_driver", return_value=mock_driver):
        from app.core.kb.writer.neo4j_writer import delete_by_standard_no
        result = await delete_by_standard_no("GB/T-001", errors)

    assert result is False
    assert len(errors) == 1
    assert "neo4j unreachable" in errors[0]


# ── write_batch ────────────────────────────────────────────────────────

async def test_write_batch_creates_document_and_chunks():
    """write_batch 执行包含 MERGE Document 和 UNWIND chunks 的 Cypher"""
    mock_session = AsyncMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    chunks = [_make_chunk("c1"), _make_chunk("c2")]

    with patch("app.core.kb.writer.neo4j_writer.get_neo4j_driver", return_value=mock_driver):
        from app.core.kb.writer.neo4j_writer import write_batch
        await write_batch(chunks, _make_doc_metadata())

    cypher = mock_session.run.call_args_list[0].args[0]
    params = mock_session.run.call_args_list[0].kwargs
    assert "MERGE" in cypher
    assert "UNWIND" in cypher
    assert params["standard_no"] == "GB/T-001"
    assert len(params["chunks"]) == 2
    assert params["chunks"][0]["chunk_id"] == "c1"


async def test_write_batch_creates_replaces_relation_when_present():
    """doc_metadata 有 replaces 字段时创建 REPLACES 关系"""
    mock_session = AsyncMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    meta = _make_doc_metadata(replaces=["GB/T-000"])

    with patch("app.core.kb.writer.neo4j_writer.get_neo4j_driver", return_value=mock_driver):
        from app.core.kb.writer.neo4j_writer import write_batch
        await write_batch([], meta)

    # 主写入 + 1次 REPLACES 关系写入
    assert mock_session.run.call_count == 2
    replaces_cypher = mock_session.run.call_args_list[1].args[0]
    assert "REPLACES" in replaces_cypher


async def test_write_batch_skips_replaces_when_absent():
    """doc_metadata 无 replaces 字段时不创建 REPLACES 关系"""
    mock_session = AsyncMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.core.kb.writer.neo4j_writer.get_neo4j_driver", return_value=mock_driver):
        from app.core.kb.writer.neo4j_writer import write_batch
        await write_batch([], _make_doc_metadata())

    assert mock_session.run.call_count == 1


async def test_write_batch_creates_replaced_by_relation_when_present():
    """doc_metadata 有 replaced_by 字段时创建 REPLACED_BY 关系"""
    mock_session = AsyncMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    meta = _make_doc_metadata(replaced_by=["GB/T-002"])

    with patch("app.core.kb.writer.neo4j_writer.get_neo4j_driver", return_value=mock_driver):
        from app.core.kb.writer.neo4j_writer import write_batch
        await write_batch([], meta)

    # 主写入 + 1次 REPLACED_BY 关系写入
    assert mock_session.run.call_count == 2
    replaced_by_cypher = mock_session.run.call_args_list[1].args[0]
    assert "REPLACED_BY" in replaced_by_cypher


# ── write_one ──────────────────────────────────────────────────────────

async def test_write_one_creates_single_chunk():
    """write_one 写入单个 chunk 并建立 HAS_CHUNK 关系"""
    mock_session = AsyncMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    chunk = _make_chunk("c1")

    with patch("app.core.kb.writer.neo4j_writer.get_neo4j_driver", return_value=mock_driver):
        from app.core.kb.writer.neo4j_writer import write_one
        await write_one(chunk, _make_doc_metadata())

    cypher = mock_session.run.call_args.args[0]
    params = mock_session.run.call_args.kwargs
    assert "HAS_CHUNK" in cypher
    assert params["chunk_id"] == "c1"
