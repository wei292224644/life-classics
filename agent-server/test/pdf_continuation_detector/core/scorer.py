"""
评分引擎（加权打分）

负责调用所有规则函数，累加分数，收集判定原因。
不在此处做最终 is_continuation 判定。
"""

from typing import Tuple, List
from .models import PageContext
from . import rules


def score_page_continuation(context: PageContext) -> Tuple[int, List[str]]:
    """
    计算页面延续分数
    
    调用所有规则函数，累加分数增量，收集所有非空的判定原因。
    不在此处做最终 is_continuation 判定。
    
    Args:
        context: 页面上下文，包含当前页和上一页的信息
        
    Returns:
        (total_score, reasons)
        - total_score: 累加后的总分（整数）
        - reasons: 所有非空的判定原因列表
    """
    total_score = 0
    reasons: List[str] = []
    
    # 定义所有规则函数
    rule_functions = [
        rules.rule_no_title_at_page_start,
        rules.rule_new_section_detected,
        rules.rule_list_continuation,
        rules.rule_prev_sentence_unfinished,
        rules.rule_continued_table,
        rules.rule_embedding_similarity,
    ]
    
    # 调用所有规则函数
    for rule_func in rule_functions:
        score_delta, reason = rule_func(context)
        
        # 累加分数
        total_score += score_delta
        
        # 收集非空原因
        if reason:
            reasons.append(reason)
    
    return total_score, reasons
