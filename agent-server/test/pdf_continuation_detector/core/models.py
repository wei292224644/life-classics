"""
数据结构定义
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PageContext:
    """
    页面上下文信息
    
    用于存储当前页和上一页的文本信息，用于判断页面间的延续关系。
    
    Attributes:
        page_index: 当前页的索引（从 0 开始）
        current_page_text: 当前页的完整文本内容
        previous_page_text: 上一页的完整文本内容
        current_page_lines: 当前页的文本行列表
        previous_page_lines: 上一页的文本行列表
        embedding_similarity: 嵌入向量相似度（可选，用于语义相似度判断）
    """
    page_index: int
    current_page_text: str
    previous_page_text: str
    current_page_lines: List[str]
    previous_page_lines: List[str]
    embedding_similarity: Optional[float] = None
    
    def __post_init__(self):
        """初始化后处理：确保列表不为 None"""
        if self.current_page_lines is None:
            self.current_page_lines = []
        if self.previous_page_lines is None:
            self.previous_page_lines = []


@dataclass
class ContinuationResult:
    """
    延续判定结果
    
    存储判定页面是否为上一页延续的结果信息。
    
    Attributes:
        is_continuation: 是否为延续（True 表示延续，False 表示不延续）
        score: 判定分数（整数，用于量化延续程度）
        reasons: 判定原因列表（说明判定依据）
    """
    is_continuation: bool
    score: int
    reasons: List[str]
    
    def __post_init__(self):
        """初始化后处理：确保列表不为 None"""
        if self.reasons is None:
            self.reasons = []
