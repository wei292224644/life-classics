"""
Markdown 文件导入模块
"""

import os
from langchain_core.documents import Document
from langchain_community.document_loaders import UnstructuredMarkdownLoader


def import_markdown(file_path: str, strategy: str) -> Document:
    """
    导入 Markdown 文件

    Args:
        file_path: Markdown 文件路径
        strategy: 切分策略

    Returns:
        Document 对象，包含 Markdown 内容
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    loader = UnstructuredMarkdownLoader(file_path)
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
            "source_format": "markdown",
            "strategy": strategy,
        },
    )
