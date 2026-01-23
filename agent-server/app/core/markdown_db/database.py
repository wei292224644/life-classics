"""
Markdown 数据库操作类
使用 SQLite 存储 document 和 markdown 之间的关系，以及 markdown 文本内容
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.core.config import settings


class MarkdownDB:
    """Markdown 数据库操作类"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径，如果为 None，使用默认路径
        """
        if db_path is None:
            # 默认数据库路径：项目根目录下的 markdown_db.sqlite
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = str(project_root / "markdown_db.sqlite")

        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _save_to_debug_file(self, markdown_id: str, content: str):
        """
        保存 markdown 内容到文件（仅用于 debug）
        
        这是一个内部方法，外部代码不应该直接调用。
        文件操作失败不会影响主流程。

        Args:
            markdown_id: markdown 的唯一标识
            content: markdown 文本内容
        """
        try:
            markdown_cache_dir = Path(settings.MARKDOWN_CACHE_DIR)
            markdown_cache_dir.mkdir(parents=True, exist_ok=True)
            markdown_path = markdown_cache_dir / f"{markdown_id}.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            # 文件写入失败不影响主流程，只记录警告
            print(f"警告: 保存 markdown 到文件失败（仅用于 debug）: {e}")

    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建 markdowns 表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS markdowns (
                markdown_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                doc_title TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 创建索引以提高查询性能
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_doc_id ON markdowns(doc_id)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_markdown_id ON markdowns(markdown_id)
        """
        )

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        # 设置返回字典格式的 row_factory
        conn.row_factory = sqlite3.Row
        return conn

    def insert_markdown(
        self,
        markdown_id: str,
        doc_id: str,
        content: str,
        doc_title: Optional[str] = None,
    ) -> bool:
        """
        插入或更新 markdown 记录

        Args:
            markdown_id: markdown 的唯一标识
            doc_id: 文档 ID
            content: markdown 文本内容
            doc_title: 文档标题（可选）

        Returns:
            是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 检查记录是否已存在
            cursor.execute(
                "SELECT markdown_id FROM markdowns WHERE markdown_id = ?",
                (markdown_id,),
            )
            exists = cursor.fetchone() is not None

            if exists:
                # 更新现有记录
                cursor.execute(
                    """
                    UPDATE markdowns
                    SET doc_id = ?, doc_title = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE markdown_id = ?
                    """,
                    (doc_id, doc_title, content, markdown_id),
                )
            else:
                # 插入新记录
                cursor.execute(
                    """
                    INSERT INTO markdowns (markdown_id, doc_id, doc_title, content)
                    VALUES (?, ?, ?, ?)
                    """,
                    (markdown_id, doc_id, doc_title or doc_id, content),
                )

            conn.commit()
            conn.close()
            
            # 保存到文件（debug，不影响主流程）
            self._save_to_debug_file(markdown_id, content)
            
            return True
        except Exception as e:
            print(f"插入 markdown 记录失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def get_markdown(self, markdown_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 markdown_id 获取 markdown 记录

        Args:
            markdown_id: markdown 的唯一标识

        Returns:
            markdown 记录字典，如果不存在返回 None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM markdowns WHERE markdown_id = ?",
                (markdown_id,),
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"获取 markdown 记录失败: {e}")
            return None

    def get_markdowns_by_doc_id(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        根据 doc_id 获取所有相关的 markdown 记录

        Args:
            doc_id: 文档 ID

        Returns:
            markdown 记录列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM markdowns WHERE doc_id = ? ORDER BY created_at DESC",
                (doc_id,),
            )
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取 markdown 记录列表失败: {e}")
            return []

    def update_markdown_content(self, markdown_id: str, content: str) -> bool:
        """
        更新 markdown 内容

        Args:
            markdown_id: markdown 的唯一标识
            content: 新的 markdown 文本内容

        Returns:
            是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE markdowns
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE markdown_id = ?
                """,
                (content, markdown_id),
            )

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            # 保存到文件（debug，不影响主流程）
            if affected_rows > 0:
                self._save_to_debug_file(markdown_id, content)

            return affected_rows > 0
        except Exception as e:
            print(f"更新 markdown 内容失败: {e}")
            return False

    def delete_markdown(self, markdown_id: str) -> bool:
        """
        删除 markdown 记录

        Args:
            markdown_id: markdown 的唯一标识

        Returns:
            是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM markdowns WHERE markdown_id = ?",
                (markdown_id,),
            )

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            return affected_rows > 0
        except Exception as e:
            print(f"删除 markdown 记录失败: {e}")
            return False

    def delete_markdowns_by_doc_id(self, doc_id: str) -> int:
        """
        删除指定 doc_id 的所有 markdown 记录

        Args:
            doc_id: 文档 ID

        Returns:
            删除的记录数
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM markdowns WHERE doc_id = ?",
                (doc_id,),
            )

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            return affected_rows
        except Exception as e:
            print(f"删除 markdown 记录列表失败: {e}")
            return 0

    def get_all_markdowns(self) -> List[Dict[str, Any]]:
        """
        获取所有 markdown 记录

        Returns:
            markdown 记录列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM markdowns ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取所有 markdown 记录失败: {e}")
            return []

    def get_doc_ids(self) -> List[str]:
        """
        获取所有唯一的 doc_id 列表

        Returns:
            doc_id 列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT doc_id FROM markdowns")
            rows = cursor.fetchall()
            conn.close()

            return [row["doc_id"] for row in rows]
        except Exception as e:
            print(f"获取 doc_id 列表失败: {e}")
            return []

    def get_markdown_ids_by_doc_id(self, doc_id: str) -> List[str]:
        """
        根据 doc_id 获取所有相关的 markdown_id 列表

        Args:
            doc_id: 文档 ID

        Returns:
            markdown_id 列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT markdown_id FROM markdowns WHERE doc_id = ?",
                (doc_id,),
            )
            rows = cursor.fetchall()
            conn.close()

            return [row["markdown_id"] for row in rows]
        except Exception as e:
            print(f"获取 markdown_id 列表失败: {e}")
            return []

    def clear_all(self) -> int:
        """
        清空所有 markdown 记录

        Returns:
            删除的记录数
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 获取删除前的记录数
            cursor.execute("SELECT COUNT(*) as count FROM markdowns")
            count = cursor.fetchone()["count"]

            # 删除所有记录
            cursor.execute("DELETE FROM markdowns")

            conn.commit()
            conn.close()

            return count
        except Exception as e:
            print(f"清空所有记录失败: {e}")
            return 0
