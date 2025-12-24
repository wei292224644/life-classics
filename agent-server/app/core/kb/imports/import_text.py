"""
Text 文件导入模块
"""

from langchain_core.documents import Document
import os


def import_text(file_path: str, strategy: str) -> Document:
    """
    导入 Text 文件

    Args:
        file_path: Text 文件路径
        strategy: 切分策略

    Returns:
        Document 对象，包含 Text 内容
    """
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()
    if not documents:
        return []
    content = documents[0].page_content
    return Document(
        page_content=content,
        metadata={
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "file_type": os.path.splitext(file_path)[1],
            "source_format": "text",
            "strategy": strategy,
        },
    )
