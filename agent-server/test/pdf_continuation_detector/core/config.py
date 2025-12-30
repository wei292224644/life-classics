"""
权重与阈值配置

所有规则权重集中在此文件中，便于统一管理和调参。
"""

from typing import Dict


# ============================================================================
# 规则权重配置
# ============================================================================

# 页面开头无标题权重
# 语义：如果当前页开头没有章节标题、表格标题等，说明可能是上一页内容的延续
# 权重越高，该规则对判定延续的影响越大
NO_TITLE_AT_PAGE_START: int = 40

# 列表延续权重
# 语义：如果上一页和当前页都包含列表项，且列表项连续，说明是列表的跨页延续
# 例如：上一页以 "3. 第三项" 结尾，当前页以 "4. 第四项" 开头
LIST_CONTINUATION: int = 20

# 上一页句子未完成权重
# 语义：如果上一页最后一行是未完成的句子（以逗号、顿号等中间标点结尾），
#       且当前页开头继续该句子，说明是句子跨页延续
PREV_SENTENCE_UNFINISHED: int = 20

# 嵌入向量高相似度权重
# 语义：如果使用嵌入向量计算的两页文本相似度很高，说明语义上相关，可能是延续
# 注意：此权重需要配合 embedding_similarity 字段使用
EMBEDDING_HIGH_SIMILARITY: int = 20

# 表格延续权重
# 语义：如果上一页包含表格，且当前页继续该表格（包含表格字符或表格行），
#       说明是表格的跨页延续
CONTINUED_TABLE: int = 30

# 新章节惩罚权重（负值）
# 语义：如果当前页开头包含新的章节标题，说明不是延续，而是新章节的开始
# 使用负权重表示惩罚，降低延续分数
NEW_SECTION_PENALTY: int = -40


# ============================================================================
# 判定阈值配置
# ============================================================================

# 延续判定阈值
# 语义：当所有规则的加权总分达到或超过此阈值时，判定为延续
# 总分 = 各规则得分 × 对应权重（如果规则匹配）
CONTINUATION_THRESHOLD: int = 50


# ============================================================================
# 规则权重字典（便于统一管理和调参）
# ============================================================================

# 规则权重映射表
# 格式：{规则名称: 权重值}
# 注意：权重值可以是正数（支持延续）或负数（不支持延续）
RULE_WEIGHTS: Dict[str, int] = {
    "no_title_at_page_start": NO_TITLE_AT_PAGE_START,
    "list_continuation": LIST_CONTINUATION,
    "prev_sentence_unfinished": PREV_SENTENCE_UNFINISHED,
    "embedding_high_similarity": EMBEDDING_HIGH_SIMILARITY,
    "continued_table": CONTINUED_TABLE,
    "new_section_penalty": NEW_SECTION_PENALTY,
}


# ============================================================================
# 辅助函数
# ============================================================================

def get_rule_weight(rule_name: str) -> int:
    """
    获取指定规则的权重
    
    Args:
        rule_name: 规则名称
        
    Returns:
        规则权重值，如果规则不存在则返回 0
    """
    return RULE_WEIGHTS.get(rule_name, 0)


def get_all_weights() -> Dict[str, int]:
    """
    获取所有规则权重
    
    Returns:
        规则权重字典
    """
    return RULE_WEIGHTS.copy()


def update_rule_weight(rule_name: str, weight: int) -> None:
    """
    更新指定规则的权重
    
    Args:
        rule_name: 规则名称
        weight: 新的权重值
    """
    RULE_WEIGHTS[rule_name] = weight
