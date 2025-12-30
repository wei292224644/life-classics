"""
单条规则实现（纯规则函数）

每个规则函数独立判断，返回分数增量和原因。
规则内部只做判断，不做总分累加。
"""

from typing import Tuple, Optional
from pathlib import Path
import importlib.util

# 动态导入 utils 模块（避免导入路径问题）
utils_path = Path(__file__).parent.parent / "utils"
text_utils_path = utils_path / "text_utils.py"
regex_patterns_path = utils_path / "regex_patterns.py"

spec = importlib.util.spec_from_file_location("text_utils", text_utils_path)
text_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(text_utils)

spec = importlib.util.spec_from_file_location("regex_patterns", regex_patterns_path)
regex_patterns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(regex_patterns)

# 导入工具函数
from .config import (
    NO_TITLE_AT_PAGE_START,
    NEW_SECTION_PENALTY,
    LIST_CONTINUATION,
    PREV_SENTENCE_UNFINISHED,
    CONTINUED_TABLE,
    EMBEDDING_HIGH_SIMILARITY,
)

# 导入模型
from .models import PageContext


def rule_no_title_at_page_start(context: PageContext) -> Tuple[int, Optional[str]]:
    """
    规则：页面开头无标题
    
    判断当前页开头是否没有章节/条款标题。
    如果当前页开头没有标题，说明可能是上一页内容的延续。
    
    Args:
        context: 页面上下文
        
    Returns:
        (score_delta, reason)
        - score_delta: 如果匹配则返回权重值，否则返回 0
        - reason: 判定原因，如果不匹配则返回 None
    """
    # 检查当前页开头是否有章节标题
    has_title = text_utils.has_section_title_at_start(context.current_page_lines)
    
    if not has_title:
        return NO_TITLE_AT_PAGE_START, "当前页开头无章节标题，可能是延续"
    
    return 0, None


def rule_new_section_detected(context: PageContext) -> Tuple[int, Optional[str]]:
    """
    规则：检测到新章节
    
    判断当前页开头是否包含新的章节/条款标题。
    如果检测到新章节，说明不是延续，而是新章节的开始。
    此规则返回负值（惩罚），降低延续分数。
    
    Args:
        context: 页面上下文
        
    Returns:
        (score_delta, reason)
        - score_delta: 如果匹配则返回惩罚权重值（负值），否则返回 0
        - reason: 判定原因，如果不匹配则返回 None
    """
    # 检查当前页开头是否有章节标题
    has_title = text_utils.has_section_title_at_start(context.current_page_lines)
    
    if has_title:
        # 提取章节标题
        section_title = regex_patterns.extract_section_title(context.current_page_text)
        if section_title:
            return NEW_SECTION_PENALTY, f"检测到新章节标题：{section_title}"
        else:
            return NEW_SECTION_PENALTY, "检测到新章节标题"
    
    return 0, None


def rule_list_continuation(context: PageContext) -> Tuple[int, Optional[str]]:
    """
    规则：列表延续
    
    判断上一页和当前页的列表项是否连续（如 a) → b)）。
    如果列表项连续，说明是列表的跨页延续。
    
    Args:
        context: 页面上下文
        
    Returns:
        (score_delta, reason)
        - score_delta: 如果匹配则返回权重值，否则返回 0
        - reason: 判定原因，如果不匹配则返回 None
    """
    # 检查列表是否连续
    is_continuation = text_utils.is_list_continuation(
        context.previous_page_lines,
        context.current_page_lines
    )
    
    if is_continuation:
        # 获取上一页末尾和当前页开头的列表项
        prev_end = text_utils.get_page_end_lines(context.previous_page_lines, n=3)
        curr_start = text_utils.get_page_start_lines(context.current_page_lines, n=3)
        
        # 查找列表项
        prev_item = None
        curr_item = None
        
        for line in reversed(prev_end):
            if regex_patterns.is_list_item(line):
                prev_item = line.strip()
                break
        
        for line in curr_start:
            if regex_patterns.is_list_item(line):
                curr_item = line.strip()
                break
        
        if prev_item and curr_item:
            return LIST_CONTINUATION, f"列表延续：{prev_item[:30]}... → {curr_item[:30]}..."
        else:
            return LIST_CONTINUATION, "列表延续"
    
    return 0, None


def rule_prev_sentence_unfinished(context: PageContext) -> Tuple[int, Optional[str]]:
    """
    规则：上一页句子未完成
    
    判断上一页最后一行是否是未完成的句子。
    如果上一页句子未完成，说明句子可能在当前页继续。
    
    Args:
        context: 页面上下文
        
    Returns:
        (score_delta, reason)
        - score_delta: 如果匹配则返回权重值，否则返回 0
        - reason: 判定原因，如果不匹配则返回 None
    """
    if not context.previous_page_lines:
        return 0, None
    
    # 获取上一页末尾的行
    prev_end = text_utils.get_page_end_lines(context.previous_page_lines, n=1)
    
    if not prev_end:
        return 0, None
    
    # 检查最后一行是否未完成
    last_line = prev_end[0]
    is_unfinished = text_utils.is_sentence_unfinished(last_line)
    
    if is_unfinished:
        return PREV_SENTENCE_UNFINISHED, f"上一页句子未完成：{last_line[:50]}..."
    
    return 0, None


def rule_continued_table(context: PageContext) -> Tuple[int, Optional[str]]:
    """
    规则：表格延续
    
    判断上一页和当前页是否包含表格，且表格是否延续。
    如果检测到表格延续标记或表格行连续，说明是表格的跨页延续。
    
    Args:
        context: 页面上下文
        
    Returns:
        (score_delta, reason)
        - score_delta: 如果匹配则返回权重值，否则返回 0
        - reason: 判定原因，如果不匹配则返回 None
    """
    # 检查当前页是否包含表格延续标记（检查全文和前10行）
    if regex_patterns.is_continued_table(context.current_page_text):
        return CONTINUED_TABLE, "检测到表格延续标记"
    
    # 检查当前页前10行是否包含表格延续标记（放宽检测范围）
    curr_start_extended = text_utils.get_page_start_lines(context.current_page_lines, n=10)
    curr_start_text = "\n".join(curr_start_extended)
    if regex_patterns.is_continued_table(curr_start_text):
        return CONTINUED_TABLE, "检测到表格延续标记（前10行）"
    
    # 检查上一页末尾和当前页开头是否都包含表格相关字符（放宽到10行）
    prev_end = text_utils.get_page_end_lines(context.previous_page_lines, n=10)
    curr_start = text_utils.get_page_start_lines(context.current_page_lines, n=10)
    
    # 检查是否包含表格字符（|、┃、│ 等）
    prev_has_table = any('|' in line or '┃' in line or '│' in line for line in prev_end)
    curr_has_table = any('|' in line or '┃' in line or '│' in line for line in curr_start)
    
    if prev_has_table and curr_has_table:
        return CONTINUED_TABLE, "检测到表格跨页延续（表格字符连续）"
    
    # 检查上一页是否包含表格标题（如"表 A.1"），当前页是否继续表格内容
    # 如果上一页有表格标题，当前页开头有表格字符，也可能是延续
    prev_text_lower = context.previous_page_text.lower()
    has_table_title = (
        '表' in context.previous_page_text and 
        ('a.' in prev_text_lower or 'b.' in prev_text_lower or 
         any(f'表 {i}' in context.previous_page_text for i in range(1, 100)))
    )
    
    if has_table_title and curr_has_table:
        return CONTINUED_TABLE, "检测到表格延续（上一页有表格标题，当前页有表格内容）"
    
    return 0, None


def rule_embedding_similarity(context: PageContext) -> Tuple[int, Optional[str]]:
    """
    规则：嵌入向量相似度
    
    判断上一页和当前页的嵌入向量相似度是否很高。
    如果相似度很高，说明语义上相关，可能是延续。
    
    Args:
        context: 页面上下文（需要包含 embedding_similarity 字段）
        
    Returns:
        (score_delta, reason)
        - score_delta: 如果相似度足够高则返回权重值，否则返回 0
        - reason: 判定原因，如果不匹配则返回 None
    """
    # 检查是否有嵌入向量相似度数据
    if context.embedding_similarity is None:
        return 0, None
    
    # 相似度阈值（可根据实际情况调整）
    similarity_threshold = 0.7
    
    if context.embedding_similarity >= similarity_threshold:
        similarity_percent = int(context.embedding_similarity * 100)
        return EMBEDDING_HIGH_SIMILARITY, f"嵌入向量相似度高：{similarity_percent}%"
    
    return 0, None
