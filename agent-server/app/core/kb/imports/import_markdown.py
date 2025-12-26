"""
Markdown 文件导入模块
"""

import os
from langchain_core.documents import Document
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from typing import List

from app.core.document_chunk import ContentType, DocumentChunk


def import_markdown(file_path: str) -> List[DocumentChunk]:
    """
    导入 Markdown 文件

    Args:
        file_path: Markdown 文件路径

    Returns:
        DocumentChunk 对象，包含 Markdown 内容
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    loader = UnstructuredMarkdownLoader(file_path)
    documents = loader.load()
    if not documents:
        return []
    content = documents[0].page_content

    return [
        DocumentChunk(
            doc_id=os.path.basename(file_path),
            doc_title=os.path.basename(file_path),
            section_path=[],
            content_type=ContentType.NOTE,
            content=content,
            meta={
                "file_name": os.path.basename(file_path),
                "file_path": file_path,
                "source_format": "markdown",
            },
        )
    ]
