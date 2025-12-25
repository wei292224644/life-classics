"""
文本切分策略
按照段落、句子等文本单位进行切分
"""

from typing import List, Dict, Any

from langchain_core.documents import Document


def split_text(documents: List[Document], **options) -> List[Document]:
    """
    标题切分策略

    Args:
        document: 待切分的文档
        **options: 其他参数



    Returns:
        切分后的知识库通用数据结构列表
    """
    # TODO: 实现标题切分逻辑
    pass
