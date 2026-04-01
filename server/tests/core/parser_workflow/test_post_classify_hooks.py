import pytest
from workflow_parser_kb.models import TypedSegment
from workflow_parser_kb.post_classify_hooks import (
    merge_formula_preamble,
    merge_procedure_list,
    POST_CLASSIFY_HOOKS,
)

_CALC_PARAMS = {
    "strategy": "formula_embed",
    "prompt_template": "将以下计算公式及变量说明转化为可检索的混合文本。",
}
_PLAIN_PARAMS = {
    "strategy": "plain_embed",
    "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n",
}


def _seg(content, structure_type, semantic_type, params=None) -> TypedSegment:
    return TypedSegment(
        content=content,
        structure_type=structure_type,
        semantic_type=semantic_type,
        transform_params=params or _PLAIN_PARAMS,
        confidence=0.95,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )


FORMULA = "$$\nX = \\frac{C \\times V}{m}\n$$\n\n式中：\n\nX——残留量，μg/kg；\nC——浓度，ng/mL；\nV——体积，mL；\nm——质量，g。"
PREAMBLE = "试料中甲砜霉素的残留量（μg/kg）按下式计算："


def test_merge_formula_preamble_merges_preamble_and_formula():
    """calculation paragraph 紧随 formula segment 时应合并为一个 formula segment。"""
    segments = [
        _seg(PREAMBLE, "paragraph", "calculation", _CALC_PARAMS),
        _seg(FORMULA, "formula", "calculation", _CALC_PARAMS),
    ]
    result = merge_formula_preamble(segments)
    assert len(result) == 1
    assert result[0]["structure_type"] == "formula"
    assert result[0]["semantic_type"] == "calculation"
    assert PREAMBLE in result[0]["content"]
    assert FORMULA in result[0]["content"]


def test_merge_formula_preamble_no_merge_when_different_semantic():
    """paragraph.semantic_type != formula.semantic_type 时不合并。"""
    segments = [
        _seg("步骤说明段落", "paragraph", "procedure"),
        _seg(FORMULA, "formula", "calculation", _CALC_PARAMS),
    ]
    result = merge_formula_preamble(segments)
    assert len(result) == 2


def test_merge_formula_preamble_no_merge_when_not_adjacent_formula():
    """calculation paragraph 后面不是 formula 时不合并。"""
    segments = [
        _seg(PREAMBLE, "paragraph", "calculation", _CALC_PARAMS),
        _seg("其他段落内容", "paragraph", "calculation", _CALC_PARAMS),
    ]
    result = merge_formula_preamble(segments)
    assert len(result) == 2


def test_merge_formula_preamble_preserves_surrounding():
    """只合并匹配对，前后 segment 原样保留。"""
    before = _seg("前置说明", "paragraph", "procedure")
    after = _seg("结果注意事项", "paragraph", "limit")
    segments = [
        before,
        _seg(PREAMBLE, "paragraph", "calculation", _CALC_PARAMS),
        _seg(FORMULA, "formula", "calculation", _CALC_PARAMS),
        after,
    ]
    result = merge_formula_preamble(segments)
    assert len(result) == 3
    assert result[0]["content"] == before["content"]
    assert result[2]["content"] == after["content"]


# ── merge_procedure_list ────────────────────────────────────────────────────

PROC_INTRO = "取适量新鲜或冷藏的空白或供试牛奶，混合均匀。"
PROC_LIST = "取均质后的供试样品，作为供试试料。取均质后的空白样品，作为空白试料。"


def test_merge_procedure_list_merges_intro_and_list():
    """procedure paragraph + procedure list 相邻时应合并为一个 list segment。"""
    segments = [
        _seg(PROC_INTRO, "paragraph", "procedure"),
        _seg(PROC_LIST, "list", "procedure"),
    ]
    result = merge_procedure_list(segments)
    assert len(result) == 1
    assert result[0]["structure_type"] == "list"
    assert result[0]["semantic_type"] == "procedure"
    assert PROC_INTRO in result[0]["content"]
    assert PROC_LIST in result[0]["content"]


def test_merge_procedure_list_no_merge_different_semantic():
    """paragraph.semantic_type != list.semantic_type 时不合并。"""
    segments = [
        _seg("通用试剂说明", "paragraph", "material"),
        _seg(PROC_LIST, "list", "procedure"),
    ]
    result = merge_procedure_list(segments)
    assert len(result) == 2


def test_merge_procedure_list_no_merge_same_type_not_list():
    """procedure paragraph + procedure paragraph（不是 list）不合并。"""
    segments = [
        _seg(PROC_INTRO, "paragraph", "procedure"),
        _seg("另一段步骤说明", "paragraph", "procedure"),
    ]
    result = merge_procedure_list(segments)
    assert len(result) == 2


def test_merge_procedure_list_preserves_surrounding():
    """只合并匹配对，前后 segment 原样保留。"""
    before = _seg("章节标题", "header", "metadata")
    after = _seg("保存条件", "paragraph", "procedure")
    segments = [
        before,
        _seg(PROC_INTRO, "paragraph", "procedure"),
        _seg(PROC_LIST, "list", "procedure"),
        after,
    ]
    result = merge_procedure_list(segments)
    assert len(result) == 3
    assert result[0]["content"] == before["content"]
    assert result[2]["content"] == after["content"]


# ── 跨 hook 链式合并 ─────────────────────────────────────────────────────────

def test_hooks_chain_preamble_formula_variables():
    """三段连续：导言 → 公式 → 变量说明，两个 hook 依次执行后应合并为一个 segment。

    hook 1 (merge_formula_preamble) 先将导言+公式合并为 formula segment，
    hook 2 (merge_formula_with_variables) 再将合并结果与变量说明合并。
    """
    from workflow_parser_kb.post_classify_hooks import (
        merge_formula_with_variables,
        POST_CLASSIFY_HOOKS,
    )

    VARIABLES = "式中：\n\nX——残留量，μg/kg；\nC——浓度，ng/mL；"
    segments = [
        _seg(PREAMBLE, "paragraph", "calculation", _CALC_PARAMS),
        _seg(FORMULA, "formula", "calculation", _CALC_PARAMS),
        _seg(VARIABLES, "list", "calculation", _CALC_PARAMS),
    ]

    # 模拟 POST_CLASSIFY_HOOKS 中 hook1 → hook2 的执行顺序
    result = segments
    for hook in [merge_formula_preamble, merge_formula_with_variables]:
        result = hook(result)

    assert len(result) == 1
    assert result[0]["structure_type"] == "formula"
    assert PREAMBLE in result[0]["content"]
    assert FORMULA in result[0]["content"]
    assert VARIABLES in result[0]["content"]


# ── POST_CLASSIFY_HOOKS 注册表 ───────────────────────────────────────────────

def test_post_classify_hooks_is_list_of_callables():
    """POST_CLASSIFY_HOOKS 应是可调用函数的列表。"""
    assert isinstance(POST_CLASSIFY_HOOKS, list)
    assert all(callable(h) for h in POST_CLASSIFY_HOOKS)
    assert len(POST_CLASSIFY_HOOKS) == 4


def test_post_classify_hooks_contains_all_four():
    """注册表应包含全部 4 个 hook（顺序不限）。"""
    from workflow_parser_kb.post_classify_hooks import (
        merge_formula_preamble,
        merge_formula_with_variables,
        merge_procedure_list,
        merge_short_segments,
    )
    for hook in [merge_formula_preamble, merge_formula_with_variables,
                 merge_procedure_list, merge_short_segments]:
        assert hook in POST_CLASSIFY_HOOKS
