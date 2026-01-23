"""
Markdown 数据库模块
用于存储 document 和 markdown 之间的关系，以及 markdown 本身的文本信息
"""

from pathlib import Path
from app.core.config import settings
from app.core.markdown_db.database import MarkdownDB


# 创建全局数据库实例
markdown_db = MarkdownDB(db_path=str(Path(settings.MARKDOWN_PERSIST_DIR) / "markdown_db.sqlite"))

__all__ = ["markdown_db", "MarkdownDB"]
