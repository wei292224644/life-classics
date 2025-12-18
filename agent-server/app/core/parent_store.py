"""
父 chunk 存储（SQLite）

目标：
- 向量库只存子 chunk（避免重复入库）
- 父 chunk 独立存储，供 Web UI 展示和检索回溯
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class ParentChunkStore:
    """基于 SQLite 的父 chunk 存储"""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS parent_chunks (
                    parent_id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    file_name TEXT,
                    content_type TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_parent_chunks_file_name ON parent_chunks(file_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_parent_chunks_content_type ON parent_chunks(content_type)"
            )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def upsert_parent(
        self,
        parent_id: str,
        text: str,
        metadata: Dict[str, Any],
    ) -> None:
        file_name = (metadata or {}).get("file_name")
        content_type = (metadata or {}).get("content_type")
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO parent_chunks(parent_id, text, metadata_json, file_name, content_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(parent_id) DO UPDATE SET
                    text=excluded.text,
                    metadata_json=excluded.metadata_json,
                    file_name=excluded.file_name,
                    content_type=excluded.content_type
                """,
                (parent_id, text, metadata_json, file_name, content_type, self._now_iso()),
            )

    def get_parent(self, parent_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT parent_id, text, metadata_json, file_name, content_type, created_at FROM parent_chunks WHERE parent_id=?",
                (parent_id,),
            ).fetchone()
        if not row:
            return None
        md = json.loads(row["metadata_json"] or "{}")
        return {
            "parent_id": row["parent_id"],
            "text": row["text"],
            "metadata": md,
            "file_name": row["file_name"],
            "content_type": row["content_type"],
            "created_at": row["created_at"],
        }

    def delete_parent(self, parent_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM parent_chunks WHERE parent_id=?", (parent_id,))

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM parent_chunks")

    def count(self, file_name: str = "", q: str = "") -> int:
        where, params = self._build_where(file_name=file_name, q=q)
        sql = "SELECT COUNT(1) as c FROM parent_chunks " + where
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["c"]) if row else 0

    def list_parents(
        self,
        limit: int = 20,
        offset: int = 0,
        file_name: str = "",
        q: str = "",
    ) -> Tuple[List[Dict[str, Any]], int]:
        where, params = self._build_where(file_name=file_name, q=q)
        total = self.count(file_name=file_name, q=q)
        sql = (
            "SELECT parent_id, text, metadata_json, file_name, content_type, created_at FROM parent_chunks "
            + where
            + " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        )
        params2 = list(params) + [limit, offset]
        with self._connect() as conn:
            rows = conn.execute(sql, params2).fetchall()

        items: List[Dict[str, Any]] = []
        for r in rows:
            md = json.loads(r["metadata_json"] or "{}")
            items.append(
                {
                    "parent_id": r["parent_id"],
                    "text": r["text"],
                    "metadata": md,
                    "file_name": r["file_name"],
                    "content_type": r["content_type"],
                    "created_at": r["created_at"],
                }
            )
        return items, total

    def _build_where(self, file_name: str = "", q: str = "") -> Tuple[str, List[Any]]:
        clauses = []
        params: List[Any] = []
        if file_name.strip():
            clauses.append("file_name = ?")
            params.append(file_name.strip())
        if q.strip():
            clauses.append("text LIKE ?")
            params.append(f"%{q.strip()}%")
        if not clauses:
            return "", []
        return "WHERE " + " AND ".join(clauses), params

    def list_parent_ids_by_file(self, file_name: str) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT parent_id FROM parent_chunks WHERE file_name = ?",
                (file_name,),
            ).fetchall()
        return [row["parent_id"] for row in rows]

    def delete_parents_by_file_name(self, file_name: str) -> List[str]:
        parent_ids = self.list_parent_ids_by_file(file_name)
        if not parent_ids:
            return []
        placeholders = ",".join("?" for _ in parent_ids)
        sql = f"DELETE FROM parent_chunks WHERE parent_id IN ({placeholders})"
        with self._connect() as conn:
            conn.execute(sql, parent_ids)
        return parent_ids

    def list_file_groups(self) -> List[Dict[str, Any]]:
        """按 file_name 聚合父 chunk 信息"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT file_name, content_type, COUNT(1) AS chunk_count
                FROM parent_chunks
                GROUP BY file_name, content_type
                """
            ).fetchall()
            latest_rows = conn.execute(
                """
                SELECT file_name, MAX(created_at) AS latest_created_at
                FROM parent_chunks
                GROUP BY file_name
                """
            ).fetchall()

        groups: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            file_name = row["file_name"] or "unknown"
            group = groups.setdefault(
                file_name,
                {
                    "file_name": file_name,
                    "total_parents": 0,
                    "content_types": {},
                    "latest_created_at": None,
                },
            )
            content_type = row["content_type"] or "unknown"
            chunk_count = int(row["chunk_count"] or 0)
            group["content_types"][content_type] = group["content_types"].get(content_type, 0) + chunk_count
            group["total_parents"] += chunk_count

        for row in latest_rows:
            file_name = row["file_name"] or "unknown"
            group = groups.setdefault(
                file_name,
                {
                    "file_name": file_name,
                    "total_parents": 0,
                    "content_types": {},
                    "latest_created_at": None,
                },
            )
            group["latest_created_at"] = row["latest_created_at"]

        result = list(groups.values())
        result.sort(key=lambda x: (-x["total_parents"], x["file_name"]))
        return result


