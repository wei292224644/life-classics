"""
表格切分策略
按照表格、行、列等表格单位进行切分
"""

from typing import List, Dict, Any

from app.core.document_chunk import DocumentChunk


def split_table(documents: List[DocumentChunk], **kwargs) -> List[DocumentChunk]:
    """
    表格切分策略

    Args:
        content: 待切分的表格内容
        **kwargs: 其他参数
            - row_separator: 按照行分割

    Returns:
        切分后的知识库通用数据结构列表
    """
    # TODO: 实现表格切分逻辑
    return documents
