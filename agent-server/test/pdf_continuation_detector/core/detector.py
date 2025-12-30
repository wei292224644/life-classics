"""
主入口：页面延续判定

该文件作为模块对外唯一入口，提供页面延续判定的主函数。
"""

from .models import PageContext, ContinuationResult
from .scorer import score_page_continuation
from .config import CONTINUATION_THRESHOLD


def detect_page_continuation(context: PageContext) -> ContinuationResult:
    """
    检测页面是否为上一页的延续
    
    这是模块对外唯一入口函数，负责：
    1. 调用评分器获取分数和判定原因
    2. 与阈值比较判定是否为延续
    3. 返回判定结果
    
    Args:
        context: 页面上下文，包含当前页和上一页的信息
        
    Returns:
        延续判定结果，包含：
        - is_continuation: 是否为延续
        - score: 判定分数
        - reasons: 判定原因列表
    """
    # 调用评分器获取分数和原因
    score, reasons = score_page_continuation(context)
    
    # 与阈值比较，判定是否为延续
    is_continuation = score >= CONTINUATION_THRESHOLD
    
    # 返回判定结果
    return ContinuationResult(
        is_continuation=is_continuation,
        score=score,
        reasons=reasons,
    )
