"""
文本/行处理工具函数

提供纯函数工具，不依赖全局状态，用于处理文本行和判断文本特征。
"""

from typing import List
from pathlib import Path
import importlib.util

# 动态导入 regex_patterns（避免相对导入问题）
try:
    # 尝试相对导入（正常包导入时）
    from .regex_patterns import (
        is_section_title,
        is_list_item,
        UNFINISHED_SENTENCE_PATTERN,
    )
except ImportError:
    # 如果相对导入失败，使用动态导入（动态导入时）
    utils_path = Path(__file__).parent
    regex_patterns_path = utils_path / "regex_patterns.py"
    
    spec = importlib.util.spec_from_file_location("regex_patterns", regex_patterns_path)
    regex_patterns = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(regex_patterns)
    
    is_section_title = regex_patterns.is_section_title
    is_list_item = regex_patterns.is_list_item
    UNFINISHED_SENTENCE_PATTERN = regex_patterns.UNFINISHED_SENTENCE_PATTERN


def get_page_start_lines(lines: List[str], n: int = 3) -> List[str]:
    """
    返回当前页前 n 行非空文本
    
    用途：获取页面开头的文本行，用于判断页面是否以新章节开始
    
    Args:
        lines: 文本行列表
        n: 要返回的行数，默认为 3
        
    Returns:
        前 n 行非空文本列表（按顺序）
    """
    if not lines:
        return []
    
    # 过滤空行并去除首尾空白
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    # 返回前 n 行
    return non_empty_lines[:n]


def get_page_end_lines(lines: List[str], n: int = 3) -> List[str]:
    """
    返回上一页末尾 n 行非空文本
    
    用途：获取页面结尾的文本行，用于判断页面内容是否未完成
    
    Args:
        lines: 文本行列表
        n: 要返回的行数，默认为 3
        
    Returns:
        末尾 n 行非空文本列表（按顺序）
    """
    if not lines:
        return []
    
    # 过滤空行并去除首尾空白
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    # 返回末尾 n 行
    if len(non_empty_lines) <= n:
        return non_empty_lines
    else:
        return non_empty_lines[-n:]


def has_section_title_at_start(lines: List[str]) -> bool:
    """
    判断页首是否出现章节/条款标题
    
    用途：检查页面开头是否有章节标题，如果有则说明不是延续，而是新章节
    
    Args:
        lines: 文本行列表
        
    Returns:
        如果页首出现章节/条款标题则返回 True，否则返回 False
    """
    if not lines:
        return False
    
    # 获取前几行（检查前 3 行即可）
    start_lines = get_page_start_lines(lines, n=3)
    
    # 检查是否有章节标题
    for line in start_lines:
        if is_section_title(line):
            return True
    
    return False


def is_list_continuation(prev_lines: List[str], curr_lines: List[str]) -> bool:
    """
    判断 a) → b) 这类列表是否连续
    
    用途：判断上一页的列表项和当前页的列表项是否连续，用于识别列表的跨页延续
    
    Args:
        prev_lines: 上一页的文本行列表
        curr_lines: 当前页的文本行列表
        
    Returns:
        如果列表连续则返回 True，否则返回 False
    """
    if not prev_lines or not curr_lines:
        return False
    
    # 获取上一页的最后几行和当前页的前几行
    prev_end = get_page_end_lines(prev_lines, n=3)
    curr_start = get_page_start_lines(curr_lines, n=3)
    
    # 检查上一页末尾是否有列表项
    prev_has_list = False
    prev_list_item = None
    
    for line in reversed(prev_end):  # 从后往前检查
        if is_list_item(line):
            prev_has_list = True
            prev_list_item = line.strip()
            break
    
    if not prev_has_list:
        return False
    
    # 检查当前页开头是否有列表项
    curr_has_list = False
    curr_list_item = None
    
    for line in curr_start:
        if is_list_item(line):
            curr_has_list = True
            curr_list_item = line.strip()
            break
    
    if not curr_has_list:
        return False
    
    # 判断列表项是否连续
    # 提取列表项的字母/序号
    def extract_list_marker(text: str) -> str:
        """提取列表标记（如 a)、b)、1)、2) 等）"""
        text = text.strip()
        # 匹配 a)、b)、1)、2) 等格式
        import re
        match = re.match(r'^\s*([a-zA-Z0-9]+)[\)\.]', text)
        if match:
            return match.group(1).lower()
        return ""
    
    prev_marker = extract_list_marker(prev_list_item)
    curr_marker = extract_list_marker(curr_list_item)
    
    if not prev_marker or not curr_marker:
        return False
    
    # 判断是否连续
    # 如果是字母列表（a, b, c...）
    if prev_marker.isalpha() and curr_marker.isalpha():
        if len(prev_marker) == 1 and len(curr_marker) == 1:
            prev_ord = ord(prev_marker)
            curr_ord = ord(curr_marker)
            # 检查是否是连续的字母（如 a→b, b→c）
            return curr_ord == prev_ord + 1
    
    # 如果是数字列表（1, 2, 3...）
    if prev_marker.isdigit() and curr_marker.isdigit():
        prev_num = int(prev_marker)
        curr_num = int(curr_marker)
        # 检查是否是连续的数字（如 1→2, 2→3）
        return curr_num == prev_num + 1
    
    return False


def is_sentence_unfinished(line: str) -> bool:
    """
    判断一句话是否未自然结束
    
    用途：判断句子是否未完成，用于识别句子跨页延续
    
    Args:
        line: 要检查的文本行
        
    Returns:
        如果句子未自然结束则返回 True，否则返回 False
    """
    if not line:
        return False
    
    line = line.strip()
    if not line:
        return False
    
    # 使用正则表达式检查是否匹配未完成句子的模式
    if UNFINISHED_SENTENCE_PATTERN.search(line):
        return True
    
    # 检查是否以中间标点结尾（逗号、顿号、冒号等）
    continuation_punctuation = [',', '，', '、', '：', ':', '—', '–', '-']
    if line and line[-1] in continuation_punctuation:
        return True
    
    # 检查是否以句子结束标点结尾
    ending_punctuation = ['。', '！', '？', '.', '!', '?', '；', ';']
    if line and line[-1] in ending_punctuation:
        return False
    
    # 如果行很短（少于 20 个字符）且不以标点结尾，可能是未完成的句子
    if len(line) < 20:
        return True
    
    return False
