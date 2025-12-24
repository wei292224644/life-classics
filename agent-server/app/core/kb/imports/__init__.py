"""
知识库导入模块
支持多种文件格式的导入：PDF、Markdown、JSON、Text
"""

from langchain_core.documents import Document
from .import_pdf import import_pdf
from .import_markdown import import_markdown
from .import_json import import_json
from .import_text import import_text


def import_file(file_path: str, strategy: str) -> Document:
    """
    导入文件

    Args:
        file_path: 文件路径
        strategy: 切分策略

    Returns:
        Document 对象，包含文件内容

    Raises:
        ValueError: 如果文件格式不支持
    """
    if file_path.endswith(".pdf"):
        return import_pdf(file_path, strategy)
    elif file_path.endswith(".md"):
        return import_markdown(file_path, strategy)
    elif file_path.endswith(".json"):
        return import_json(file_path, strategy)
    elif file_path.endswith(".txt"):
        return import_text(file_path, strategy)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")
