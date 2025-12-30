"""
PDF 跨页内容延续判定核心模块
"""

from .detector import detect_page_continuation
from .models import PageContext, ContinuationResult

__all__ = ["detect_page_continuation", "PageContext", "ContinuationResult"]

