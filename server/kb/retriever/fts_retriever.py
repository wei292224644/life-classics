from __future__ import annotations

import re
import sqlite3
from typing import List, Optional

import jieba

from kb.writer.fts_writer import FTS_DB_PATH


def _get_db_path(db_path: Optional[str]) -> str:
    return db_path if db_path is not None else FTS_DB_PATH


def _clean_tokens(tokens: List[str]) -> List[str]:
    """过滤掉长度 < 1 以及纯符号的 token，避免 FTS5 MATCH 语法错误。"""
    return [t for t in tokens if len(t) >= 1 and not re.match(r'^[\W_]+$', t)]


def query(
    query_text: str,
    top_k: int = 20,
    filters: dict | None = None,
    db_path: str | None = None,
) -> List[tuple[str, float]]:
    """用 jieba 分词后执行 SQLite FTS5 BM25 查询，返回 [(chunk_id, bm25_score), ...]。

    Args:
        query_text: 查询文本，会先经 jieba 分词再拼接为 FTS5 查询串
        top_k: 返回结果数量上限
        filters: 可选过滤条件，支持 standard_no 和 semantic_type
        db_path: 可选数据库路径，默认使用 FTS_DB_PATH（测试时传 tmp_path）

    Returns:
        按 BM25 分数降序排列的 (chunk_id, score) 列表，score > 0 且越大越相关
    """
    tokens = list(jieba.cut(query_text))
    clean = _clean_tokens(tokens)
    fts_query = " ".join(clean)

    if not fts_query:
        return []

    path = _get_db_path(db_path)

    # 构建 WHERE 子句及参数
    where_clauses = ["chunks_fts MATCH ?"]
    params: list = [fts_query]

    if filters:
        if "standard_no" in filters:
            where_clauses.append("chunks.standard_no = ?")
            params.append(filters["standard_no"])
        if "semantic_type" in filters:
            where_clauses.append("chunks.semantic_type = ?")
            params.append(filters["semantic_type"])

    where_sql = " AND ".join(where_clauses)
    sql = (
        f"SELECT chunks.chunk_id, -chunks_fts.rank "
        f"FROM chunks_fts "
        f"JOIN chunks ON chunks.rowid = chunks_fts.rowid "
        f"WHERE {where_sql} "
        f"ORDER BY chunks_fts.rank "
        f"LIMIT ?"
    )
    params.append(top_k)

    try:
        with sqlite3.connect(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        # 表不存在或数据库文件尚未初始化时，返回空列表
        return []

    return [(chunk_id, float(score)) for chunk_id, score in rows]
