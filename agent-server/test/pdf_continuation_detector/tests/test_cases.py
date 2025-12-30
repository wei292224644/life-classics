"""
单元测试（覆盖典型场景）

使用 pytest 风格编写测试用例。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径（test 目录）
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入模块
from pdf_continuation_detector.core.detector import detect_page_continuation
from pdf_continuation_detector.core.models import PageContext, ContinuationResult
from pdf_continuation_detector.core.config import CONTINUATION_THRESHOLD


def test_colon_ending_with_list_start():
    """
    测试场景 1: 上一页以"："结尾，当前页以 a) 开头 → 延续
    
    这种情况通常表示上一页引出了一个列表，当前页继续该列表。
    """
    context = PageContext(
        page_index=1,
        current_page_text="a) 第一项\nb) 第二项\nc) 第三项",
        previous_page_text="检验方法包括以下内容：",
        current_page_lines=["a) 第一项", "b) 第二项", "c) 第三项"],
        previous_page_lines=["检验方法包括以下内容："],
        embedding_similarity=None,
    )
    
    result = detect_page_continuation(context)
    
    assert isinstance(result, ContinuationResult)
    assert result.is_continuation is True, f"应该判定为延续，但得到 is_continuation={result.is_continuation}, score={result.score}"
    assert result.score >= CONTINUATION_THRESHOLD, f"分数应该 >= {CONTINUATION_THRESHOLD}，但得到 {result.score}"
    assert len(result.reasons) > 0, "应该有判定原因"


def test_section_title_at_start():
    """
    测试场景 2: 当前页以"5.3 检验方法"开头 → 非延续
    
    当前页以章节标题开头，说明是新章节的开始，不是延续。
    """
    context = PageContext(
        page_index=1,
        current_page_text="5.3 检验方法\n本方法适用于...",
        previous_page_text="这是上一页的内容，已经结束了。",
        current_page_lines=["5.3 检验方法", "本方法适用于..."],
        previous_page_lines=["这是上一页的内容，已经结束了。"],
        embedding_similarity=None,
    )
    
    result = detect_page_continuation(context)
    
    assert isinstance(result, ContinuationResult)
    assert result.is_continuation is False, f"应该判定为非延续，但得到 is_continuation={result.is_continuation}, score={result.score}"
    assert result.score < CONTINUATION_THRESHOLD, f"分数应该 < {CONTINUATION_THRESHOLD}，但得到 {result.score}"
    # 应该检测到新章节
    assert any("新章节" in reason or "章节标题" in reason for reason in result.reasons), "应该检测到新章节"


def test_continued_table():
    """
    测试场景 3: 表格续页（表 3（续））→ 延续
    
    当前页包含表格延续标记，说明是表格的跨页延续。
    """
    context = PageContext(
        page_index=1,
        current_page_text="表 3（续）\n| 列1 | 列2 | 列3 |\n|-----|-----|-----|\n| 数据4 | 数据5 | 数据6 |",
        previous_page_text="表 3 示例表格\n| 列1 | 列2 | 列3 |\n|-----|-----|-----|\n| 数据1 | 数据2 | 数据3 |",
        current_page_lines=["表 3（续）", "| 列1 | 列2 | 列3 |", "|-----|-----|-----|", "| 数据4 | 数据5 | 数据6 |"],
        previous_page_lines=["表 3 示例表格", "| 列1 | 列2 | 列3 |", "|-----|-----|-----|", "| 数据1 | 数据2 | 数据3 |"],
        embedding_similarity=None,
    )
    
    result = detect_page_continuation(context)
    
    assert isinstance(result, ContinuationResult)
    assert result.is_continuation is True, f"应该判定为延续，但得到 is_continuation={result.is_continuation}, score={result.score}"
    assert result.score >= CONTINUATION_THRESHOLD, f"分数应该 >= {CONTINUATION_THRESHOLD}，但得到 {result.score}"
    # 应该检测到表格延续
    assert any("表格" in reason or "续" in reason for reason in result.reasons), "应该检测到表格延续"


def test_high_embedding_similarity():
    """
    测试场景 4: embedding_similarity > 0.8 → 延续（辅助）
    
    如果嵌入向量相似度很高，说明语义上相关，可能是延续。
    这是一个辅助规则，需要配合其他规则使用。
    """
    context = PageContext(
        page_index=1,
        current_page_text="继续上一页的内容，详细说明相关要求。",
        previous_page_text="这是上一页的内容，介绍了基本概念。",
        current_page_lines=["继续上一页的内容，详细说明相关要求。"],
        previous_page_lines=["这是上一页的内容，介绍了基本概念。"],
        embedding_similarity=0.85,  # 高相似度
    )
    
    result = detect_page_continuation(context)
    
    assert isinstance(result, ContinuationResult)
    # 高相似度应该有助于判定为延续
    # 注意：如果只有相似度，可能不足以超过阈值，但应该增加分数
    assert result.score > 0, f"分数应该 > 0，但得到 {result.score}"
    # 如果有嵌入向量相似度的原因，应该包含
    if result.score >= CONTINUATION_THRESHOLD:
        assert result.is_continuation is True
        assert any("相似度" in reason or "embedding" in reason.lower() for reason in result.reasons), "应该包含相似度相关的原因"


def test_no_rules_matched():
    """
    测试场景 5: 无任何规则命中 → 非延续
    
    如果没有任何规则匹配，分数应该为 0 或很低，判定为非延续。
    """
    context = PageContext(
        page_index=1,
        current_page_text="这是一个全新的章节。\n内容与上一页无关。",
        previous_page_text="上一页的内容已经完整结束。",
        current_page_lines=["这是一个全新的章节。", "内容与上一页无关。"],
        previous_page_lines=["上一页的内容已经完整结束。"],
        embedding_similarity=None,
    )
    
    result = detect_page_continuation(context)
    
    assert isinstance(result, ContinuationResult)
    assert result.is_continuation is False, f"应该判定为非延续，但得到 is_continuation={result.is_continuation}, score={result.score}"
    assert result.score < CONTINUATION_THRESHOLD, f"分数应该 < {CONTINUATION_THRESHOLD}，但得到 {result.score}"
    # 如果没有规则匹配，reasons 可能为空，或者只有负面的原因（如新章节）
