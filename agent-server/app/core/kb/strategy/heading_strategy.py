"""
标题切分策略
按照标题、副标题等标题单位进行切分
"""

from typing import List, Dict, Any

from langchain_core.documents import Document


def split_heading(documents: List[Document], **kwargs) -> List[Document]:
    """
    标题切分策略

    Args:
        document: 待切分的文档
        **kwargs: 其他参数

    Returns:
        切分后的知识库通用数据结构列表
    """
    # TODO: 实现标题切分逻辑
    pass
