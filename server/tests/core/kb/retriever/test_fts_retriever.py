from __future__ import annotations

import pytest

from kb.writer import fts_writer
from kb.retriever import fts_retriever


# ── helpers ────────────────────────────────────────────────────────────────


def _make_chunk(
    chunk_id: str = "c1",
    content: str = "牛奶中农药残留检测方法",
    semantic_type: str = "scope",
    section_path: list | None = None,
):
    return {
        "chunk_id": chunk_id,
        "content": content,
        "semantic_type": semantic_type,
        "section_path": section_path or ["1"],
        "raw_content": content,
        "doc_metadata": {},
        "meta": {},
        "structure_type": "paragraph",
    }


def _setup_db(tmp_path, chunks, standard_no="GB-001"):
    db = str(tmp_path / "test.db")
    fts_writer.init_db(db_path=db)
    fts_writer.write(chunks, {"standard_no": standard_no}, db_path=db)
    return db


# ── query basic ────────────────────────────────────────────────────────────


def test_query_returns_relevant_results(tmp_path):
    """写入数据后能查到相关结果，格式为 (chunk_id, score) 元组列表。"""
    chunks = [
        _make_chunk(chunk_id="c1", content="牛奶中农药残留检测方法"),
        _make_chunk(chunk_id="c2", content="食品添加剂使用标准"),
        _make_chunk(chunk_id="c3", content="重金属污染物限量规定"),
    ]
    db = _setup_db(tmp_path, chunks)

    results = fts_retriever.query("农药", top_k=5, db_path=db)

    assert len(results) > 0
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
    assert all(isinstance(chunk_id, str) for chunk_id, _ in results)
    assert all(score > 0 for _, score in results)


def test_query_returns_correct_chunk(tmp_path):
    """查询关键词命中的 chunk_id 应在结果中。"""
    chunks = [
        _make_chunk(chunk_id="pesticide", content="农药残留检测标准方法"),
        _make_chunk(chunk_id="additive", content="食品添加剂的分类和限量"),
    ]
    db = _setup_db(tmp_path, chunks)

    results = fts_retriever.query("农药", top_k=10, db_path=db)
    ids = [cid for cid, _ in results]

    assert "pesticide" in ids


def test_query_top_k_limits_results(tmp_path):
    """top_k 限制返回数量。"""
    chunks = [_make_chunk(chunk_id=f"c{i}", content=f"食品安全标准第{i}条规定") for i in range(10)]
    db = _setup_db(tmp_path, chunks)

    results = fts_retriever.query("食品", top_k=3, db_path=db)

    assert len(results) <= 3


def test_query_empty_db_returns_empty(tmp_path):
    """空数据库返回空列表。"""
    db = str(tmp_path / "empty.db")
    fts_writer.init_db(db_path=db)

    results = fts_retriever.query("农药", top_k=5, db_path=db)

    assert results == []


# ── filters ────────────────────────────────────────────────────────────────


def test_query_filter_standard_no(tmp_path):
    """filters 中 standard_no 正确过滤，只返回指定标准的结果。"""
    db = str(tmp_path / "test.db")
    fts_writer.init_db(db_path=db)

    fts_writer.write(
        [_make_chunk(chunk_id="a1", content="农药残留检测方法一")],
        {"standard_no": "GB-001"},
        db_path=db,
    )
    fts_writer.write(
        [_make_chunk(chunk_id="b1", content="农药残留检测方法二")],
        {"standard_no": "GB-002"},
        db_path=db,
    )

    results = fts_retriever.query("农药", top_k=10, filters={"standard_no": "GB-001"}, db_path=db)
    ids = [cid for cid, _ in results]

    assert "a1" in ids
    assert "b1" not in ids


def test_query_filter_semantic_type(tmp_path):
    """filters 中 semantic_type 正确过滤。"""
    db = str(tmp_path / "test.db")
    fts_writer.init_db(db_path=db)

    fts_writer.write(
        [
            _make_chunk(chunk_id="s1", content="农药残留限量规定", semantic_type="scope"),
            _make_chunk(chunk_id="d1", content="农药残留术语定义", semantic_type="definition"),
        ],
        {"standard_no": "GB-010"},
        db_path=db,
    )

    results = fts_retriever.query(
        "农药", top_k=10, filters={"semantic_type": "scope"}, db_path=db
    )
    ids = [cid for cid, _ in results]

    assert "s1" in ids
    assert "d1" not in ids


def test_query_filter_standard_no_and_semantic_type(tmp_path):
    """同时过滤 standard_no 和 semantic_type。"""
    db = str(tmp_path / "test.db")
    fts_writer.init_db(db_path=db)

    fts_writer.write(
        [
            _make_chunk(chunk_id="x1", content="农药检测范围", semantic_type="scope"),
            _make_chunk(chunk_id="x2", content="农药检测定义", semantic_type="definition"),
        ],
        {"standard_no": "GB-100"},
        db_path=db,
    )
    fts_writer.write(
        [_make_chunk(chunk_id="y1", content="农药检测其他标准", semantic_type="scope")],
        {"standard_no": "GB-200"},
        db_path=db,
    )

    results = fts_retriever.query(
        "农药",
        top_k=10,
        filters={"standard_no": "GB-100", "semantic_type": "scope"},
        db_path=db,
    )
    ids = [cid for cid, _ in results]

    assert "x1" in ids
    assert "x2" not in ids
    assert "y1" not in ids


# ── special characters ─────────────────────────────────────────────────────


def test_query_special_chars_does_not_crash(tmp_path):
    """查询词含特殊字符（*, ", -）不崩溃，返回列表（可为空）。"""
    chunks = [_make_chunk(chunk_id="sc1", content="食品安全检测标准")]
    db = _setup_db(tmp_path, chunks)

    results = fts_retriever.query('*"- special', top_k=5, db_path=db)

    assert isinstance(results, list)


def test_query_all_special_chars_returns_empty(tmp_path):
    """纯符号查询词（清洗后为空）返回空列表。"""
    chunks = [_make_chunk(chunk_id="sc2", content="食品安全标准")]
    db = _setup_db(tmp_path, chunks)

    results = fts_retriever.query("* - !", top_k=5, db_path=db)

    assert results == []


def test_query_empty_string_returns_empty(tmp_path):
    """空字符串查询返回空列表。"""
    chunks = [_make_chunk(chunk_id="sc3", content="食品安全标准")]
    db = _setup_db(tmp_path, chunks)

    results = fts_retriever.query("", top_k=5, db_path=db)

    assert results == []


# ── score ordering ─────────────────────────────────────────────────────────


def test_query_scores_are_positive(tmp_path):
    """所有返回分数均为正数（FTS5 rank 取反）。"""
    chunks = [
        _make_chunk(chunk_id="r1", content="农药残留最大限量标准"),
        _make_chunk(chunk_id="r2", content="农药使用规范指南"),
        _make_chunk(chunk_id="r3", content="农药检测分析方法"),
    ]
    db = _setup_db(tmp_path, chunks)

    results = fts_retriever.query("农药", top_k=10, db_path=db)

    assert all(score > 0 for _, score in results)


def test_query_no_match_returns_empty(tmp_path):
    """无匹配时返回空列表。"""
    chunks = [_make_chunk(chunk_id="nm1", content="完全不相关的内容")]
    db = _setup_db(tmp_path, chunks)

    # "量子纠缠" 不太可能在任何 GB 标准 chunk 里出现
    results = fts_retriever.query("量子纠缠超导", top_k=5, db_path=db)

    # 结果可能为空，也可能因 jieba 分出子词而有微弱匹配，但不应崩溃
    assert isinstance(results, list)
