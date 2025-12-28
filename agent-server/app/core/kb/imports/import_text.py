"""
Text 文件导入模块
"""

from langchain_community.document_loaders import TextLoader
import os
from pathlib import Path
from typing import List

from app.core.document_chunk import ContentType, DocumentChunk


def import_text(file_path: str, original_filename: str = None) -> List[DocumentChunk]:
    """
    导入 Text 文件

    Args:
        file_path: Text 文件路径
        original_filename: 原始文件名（如果提供，将使用此文件名作为 doc_id 和 doc_title）

    Returns:
        DocumentChunk 对象列表，包含 Text 内容
    """
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()
    if not documents:
        return []
    content = documents[0].page_content
    
    # 使用原始文件名或文件路径中的文件名
    if original_filename:
        file_name = original_filename
        doc_id = Path(original_filename).stem
        doc_title = Path(original_filename).stem
    else:
        file_name = os.path.basename(file_path)
        doc_id = file_name
        doc_title = file_name
    
    return [
        DocumentChunk(
            doc_id=doc_id,
            doc_title=doc_title,
            section_path=[],
            content_type=ContentType.NOTE,
            content=content,
            meta={
                "file_name": file_name,
                "file_path": file_path,
                "source_format": "text",
            },
        )
    ]
