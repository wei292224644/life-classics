from __future__ import annotations

import sqlite3

import pytest

from kb.writer.fts_writer import delete_by_doc_id, init_db, write


def _make_chunk(
    chunk_id: str = "c1",
    content: str = "牛奶中甲砜霉素残留检测方法",
    semantic_type: str = "scope",
    section_path: list | None = None,
):
    return {
        "chunk_id": chunk_id,
        "content": content,
        "semantic_type": semantic_type,
        "section_path": section_path or ["1", "1.1"],
        "raw_content": content,
        "doc_metadata": {},
        "meta": {},
        "structure_type": "paragraph",
    }


def _make_meta(doc_id: str = "doc-uuid-001", standard_no: str | None = "GB/T-001") -> dict:
    return {"doc_id": doc_id, "standard_no": standard_no}


# ── init_db ────────────────────────────────────────────────────────────────


def test_init_db_creates_tables(tmp_path):
    """init_db 应建立 chunks 表和 chunks_fts 虚拟表。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)

    with sqlite3.connect(db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'shadow')"
            ).fetchall()
        }
    assert "chunks" in tables
    assert "chunks_fts" in tables


def test_init_db_idempotent(tmp_path):
    """多次调用 init_db 不报错（IF NOT EXISTS）。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)
    init_db(db_path=db)  # 不应抛异常


# ── write ──────────────────────────────────────────────────────────────────


def test_write_empty_chunks_does_not_raise(tmp_path):
    """空列表不报错。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)
    write([], _make_meta(), db_path=db)  # 不应抛异常


def test_write_stores_chunk_in_base_table(tmp_path):
    """write 后 chunks 表应有对应记录。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)
    chunk = _make_chunk(chunk_id="abc123", content="食品安全国家标准")
    write([chunk], _make_meta(doc_id="doc-001", standard_no="GB 5009.1"), db_path=db)

    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT chunk_id, doc_id, standard_no, semantic_type, section_path FROM chunks WHERE chunk_id = ?",
            ("abc123",),
        ).fetchone()

    assert row is not None
    assert row[0] == "abc123"
    assert row[1] == "doc-001"
    assert row[2] == "GB 5009.1"
    assert row[3] == "scope"
    assert row[4] == "1|1.1"


def test_write_fts_match_returns_chunk(tmp_path):
    """write 后能用 FTS5 MATCH 查到对应 chunk_id。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)
    chunk = _make_chunk(chunk_id="fts001", content="食品添加剂使用标准")
    write([chunk], _make_meta(doc_id="doc-002", standard_no="GB 2760"), db_path=db)

    with sqlite3.connect(db) as conn:
        # 使用 jieba 分词后的关键词搜索
        rows = conn.execute(
            "SELECT chunk_id FROM chunks_fts WHERE chunks_fts MATCH '食品'",
        ).fetchall()

    chunk_ids = [r[0] for r in rows]
    assert "fts001" in chunk_ids


def test_write_twice_no_duplicate(tmp_path):
    """同一 standard_no 写两次（同一 chunk_id），不产生重复记录。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)
    chunk = _make_chunk(chunk_id="dup01", content="重复写入测试")
    meta = _make_meta("GB/T-002")

    write([chunk], meta, db_path=db)
    write([chunk], meta, db_path=db)

    with sqlite3.connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE chunk_id = ?", ("dup01",)
        ).fetchone()[0]
        fts_count = conn.execute(
            "SELECT COUNT(*) FROM chunks_fts WHERE chunk_id = ?", ("dup01",)
        ).fetchone()[0]

    assert count == 1
    assert fts_count == 1


def test_write_multiple_chunks(tmp_path):
    """一次写入多个 chunk，全部应可检索到。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)
    chunks = [
        _make_chunk(chunk_id=f"c{i}", content=f"标准内容第{i}条", section_path=[str(i)])
        for i in range(5)
    ]
    write(chunks, _make_meta(doc_id="doc-010"), db_path=db)

    with sqlite3.connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE doc_id = ?", ("doc-010",)
        ).fetchone()[0]

    assert count == 5


# ── delete_by_doc_id ──────────────────────────────────────────────────


def test_delete_removes_records(tmp_path):
    """delete_by_doc_id 后对应 doc_id 的记录消失。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)
    chunks = [
        _make_chunk(chunk_id="d1", content="待删除内容一"),
        _make_chunk(chunk_id="d2", content="待删除内容二"),
    ]
    write(chunks, _make_meta(doc_id="doc-del"), db_path=db)

    errors: list = []
    result = delete_by_doc_id("doc-del", errors, db_path=db)

    assert result is True
    assert errors == []

    with sqlite3.connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE doc_id = ?", ("doc-del",)
        ).fetchone()[0]
        fts_count = conn.execute(
            "SELECT COUNT(*) FROM chunks_fts WHERE chunk_id IN ('d1', 'd2')"
        ).fetchone()[0]

    assert count == 0
    assert fts_count == 0


def test_delete_nonexistent_doc_id_returns_true(tmp_path):
    """删除不存在的 doc_id 视为成功，返回 True。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)

    errors: list = []
    result = delete_by_doc_id("not-exist-uuid", errors, db_path=db)

    assert result is True
    assert errors == []


def test_delete_only_removes_target_doc(tmp_path):
    """删除某个 doc_id 不影响其他 doc_id 的记录。"""
    db = str(tmp_path / "test.db")
    init_db(db_path=db)

    write([_make_chunk(chunk_id="keep1", content="保留内容")], _make_meta(doc_id="doc-keep"), db_path=db)
    write([_make_chunk(chunk_id="del1", content="删除内容")], _make_meta(doc_id="doc-del2"), db_path=db)

    errors: list = []
    delete_by_doc_id("doc-del2", errors, db_path=db)

    with sqlite3.connect(db) as conn:
        keep_count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE doc_id = ?", ("doc-keep",)
        ).fetchone()[0]
        del_count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE doc_id = ?", ("doc-del2",)
        ).fetchone()[0]

    assert keep_count == 1
    assert del_count == 0


def test_delete_returns_false_on_error(tmp_path):
    """数据库异常时返回 False 并 append error。"""
    errors: list = []
    result = delete_by_doc_id("some-uuid", errors, db_path="/nonexistent_dir/test.db")

    assert result is False
    assert len(errors) == 1
    assert "fts delete error" in errors[0]
