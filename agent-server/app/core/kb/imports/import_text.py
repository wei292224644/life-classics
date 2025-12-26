"""
Text 文件导入模块
"""

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
import os
from typing import List

from app.core.document_chunk import ContentType, DocumentChunk


def import_text(file_path: str) -> List[DocumentChunk]:
    """
    导入 Text 文件

    Args:
        file_path: Text 文件路径

    Returns:
        DocumentChunk 对象，包含 Text 内容
    """
    loader = TextLoader(file_path, encoding="utf-8")
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
                "source_format": "text",
            },
        )
    ]
