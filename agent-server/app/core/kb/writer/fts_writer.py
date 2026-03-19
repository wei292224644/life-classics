from __future__ import annotations

import os
import sqlite3
from typing import List, Optional

import jieba

from app.core.parser_workflow.models import DocumentChunk

FTS_DB_PATH = "db/knowledge_base_fts.db"


def _get_db_path(db_path: Optional[str]) -> str:
    return db_path if db_path is not None else FTS_DB_PATH


def init_db(db_path: Optional[str] = None) -> None:
    """建 chunks 基础表 + chunks_fts 外部内容虚拟表（若已存在则跳过）。"""
    path = _get_db_path(db_path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                standard_no TEXT,
                semantic_type TEXT NOT NULL,
                section_path TEXT NOT NULL,
                tokenized_content TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                tokenized_content,
                content=chunks,
                content_rowid=rowid,
                tokenize='ascii'
            )
        """)
        conn.commit()


def write(chunks: List[DocumentChunk], doc_metadata: dict, db_path: Optional[str] = None) -> None:
    """对每个 chunk 进行 jieba 分词后写入 chunks 基础表和 chunks_fts 虚拟表。"""
    if not chunks:
        return

    path = _get_db_path(db_path)
    doc_id = doc_metadata["doc_id"]
    standard_no = doc_metadata.get("standard_no") or None

    with sqlite3.connect(path) as conn:
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            semantic_type = chunk["semantic_type"]
            section_path = "|".join(chunk["section_path"])
            tokenized_content = " ".join(jieba.cut(chunk["content"]))

            # 若已存在，先从 FTS5 索引删除旧条目（外部内容表需要手动同步）
            old = conn.execute(
                "SELECT rowid, tokenized_content FROM chunks WHERE chunk_id = ?",
                (chunk_id,),
            ).fetchone()
            if old is not None:
                old_rowid, old_tokenized = old
                conn.execute(
                    "INSERT INTO chunks_fts(chunks_fts, rowid, chunk_id, tokenized_content)"
                    " VALUES('delete', ?, ?, ?)",
                    (old_rowid, chunk_id, old_tokenized),
                )

            # 写入基础表（INSERT OR REPLACE）
            conn.execute(
                """
                INSERT OR REPLACE INTO chunks
                    (chunk_id, doc_id, standard_no, semantic_type, section_path, tokenized_content)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chunk_id, doc_id, standard_no, semantic_type, section_path, tokenized_content),
            )

            # 用新 rowid 插入 FTS5 索引
            conn.execute(
                "INSERT INTO chunks_fts(rowid, chunk_id, tokenized_content)"
                " SELECT rowid, chunk_id, tokenized_content FROM chunks WHERE chunk_id = ?",
                (chunk_id,),
            )

        conn.commit()


def delete_by_doc_id(doc_id: str, errors: List[str], db_path: Optional[str] = None) -> bool:
    """删除指定 doc_id 的所有记录。文档不存在视为成功，返回 True；异常返回 False 并 append error。"""
    path = _get_db_path(db_path)
    try:
        with sqlite3.connect(path) as conn:
            # 先获取要删除的条目，用于同步清理 FTS 索引
            rows = conn.execute(
                "SELECT rowid, chunk_id, tokenized_content FROM chunks WHERE doc_id = ?",
                (doc_id,),
            ).fetchall()

            for rowid, chunk_id, tokenized_content in rows:
                conn.execute(
                    "INSERT INTO chunks_fts(chunks_fts, rowid, chunk_id, tokenized_content)"
                    " VALUES('delete', ?, ?, ?)",
                    (rowid, chunk_id, tokenized_content),
                )

            if rows:
                conn.execute(
                    "DELETE FROM chunks WHERE doc_id = ?",
                    (doc_id,),
                )

            conn.commit()
        return True
    except Exception as e:
        errors.append(f"fts delete error: {e}")
        return False
