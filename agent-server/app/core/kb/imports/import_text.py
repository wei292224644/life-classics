"""
Text 文件导入模块
"""

import uuid
from langchain_community.document_loaders import TextLoader
import os
from pathlib import Path
from typing import List

from app.core.document_chunk import ContentType, DocumentChunk
from app.core.markdown_db import markdown_db


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
        doc_title = Path(original_filename).stem
    else:
        file_name = os.path.basename(file_path)
        doc_title = file_name
    
    # 生成 doc_id（使用 UUID）
    doc_id = uuid.uuid4().hex
    
    # 生成 markdown_id（唯一标识）
    # 使用 UUID 的前16个字符作为唯一标识
    markdown_id = uuid.uuid4().hex[:16]
    
    # 保存到数据库
    markdown_db.insert_markdown(
        markdown_id=markdown_id,
        doc_id=doc_id,
        doc_title=doc_title,
        content=content,
    )
    
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
            markdown_id=markdown_id,  # 添加 markdown_id
        )
    ]
