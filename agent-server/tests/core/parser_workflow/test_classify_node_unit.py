from unittest.mock import patch
import pytest

from app.core.parser_workflow.models import RawChunk, TypedSegment, WorkflowState
from app.core.parser_workflow.nodes.classify_node import (
    classify_node,
    _escape_for_json_prompt,
    _merge_formula_with_variables,
    _merge_short_segments,
    _MERGE_SHORT_THRESHOLD,
)
from app.core.parser_workflow.nodes.output import ClassifyOutput, SegmentItem


def _make_state(content: str, tmp_path) -> WorkflowState:
    from app.core.parser_workflow.rules import RulesStore
    store = RulesStore(str(tmp_path))
    return WorkflowState(
        md_content=content,
        doc_metadata={"standard_no": "TEST001"},
        config={},
        rules_dir=str(tmp_path),
        raw_chunks=[RawChunk(content=content, section_path=["A.3"], char_count=len(content))],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


def test_classify_node_produces_dual_type_segments(tmp_path):
    """classify_node 应产生含 structure_type + semantic_type 的 segments"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="称取试样约2g", structure_type="list", semantic_type="procedure", confidence=0.9),
    ])

    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured", return_value=mock_output):
        state = _make_state("称取试样约2g", tmp_path)
        result = classify_node(state)

    chunks = result["classified_chunks"]
    assert chunks
    seg = chunks[0]["segments"][0]
    assert seg["structure_type"] == "list"
    assert seg["semantic_type"] == "procedure"
    assert "content_type" not in seg


def test_classify_node_low_confidence_sets_unknown(tmp_path):
    """置信度低于阈值时，两个字段均应为 'unknown'"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="某段内容", structure_type="paragraph", semantic_type="scope", confidence=0.3),
    ])

    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured", return_value=mock_output):
        state = _make_state("某段内容", tmp_path)
        result = classify_node(state)

    seg = result["classified_chunks"][0]["segments"][0]
    assert seg["structure_type"] == "unknown"
    assert seg["semantic_type"] == "unknown"
    assert result["classified_chunks"][0]["has_unknown"] is True


def test_classify_node_prompt_includes_both_type_lists(tmp_path):
    """LLM 调用的 prompt 应包含 structure_types 和 semantic_types 两组描述"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="x", structure_type="paragraph", semantic_type="scope", confidence=0.9),
    ])

    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured", side_effect=capture_invoke):
        state = _make_state("x", tmp_path)
        classify_node(state)

    assert captured_prompts
    prompt = captured_prompts[0]
    for type_id in ["paragraph", "list", "table", "formula", "header"]:
        assert type_id in prompt, f"prompt 未包含 structure_type '{type_id}'"
    for type_id in ["metadata", "scope", "limit", "procedure", "material", "calculation", "definition", "amendment"]:
        assert type_id in prompt, f"prompt 未包含 semantic_type '{type_id}'"


def test_classify_node_prompt_contains_formula_rule(tmp_path):
    """prompt 中应包含公式识别确定性规则，要求含 $$ 的 segment 必须分类为 formula"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="x", structure_type="formula", semantic_type="calculation", confidence=0.9),
    ])

    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured", side_effect=capture_invoke):
        state = _make_state("x", tmp_path)
        classify_node(state)

    prompt = captured_prompts[0]
    assert "$$" in prompt, "prompt 未包含 $$ 公式规则"
    assert "structure_type=formula" in prompt, "prompt 未要求含 $$ 的 segment 用 structure_type=formula"
    assert "semantic_type=calculation" in prompt, "prompt 未要求含 $$ 的 segment 用 semantic_type=calculation"
    assert "plain_text" in prompt, "prompt 中应提到不得将公式归为 plain_text"


def test_escape_for_json_prompt_escapes_double_quotes():
    """_escape_for_json_prompt 应将所有 ASCII 双引号替换为 \\"."""
    raw = '<td rowspan="2">取适量试样</td>'
    escaped = _escape_for_json_prompt(raw)
    assert '\\"' in escaped
    assert 'rowspan=\\"2\\"' in escaped
    assert '"' not in escaped.replace('\\"', '')


def test_escape_for_json_prompt_preserves_other_characters():
    """_escape_for_json_prompt 不应修改无双引号的字符串。"""
    raw = "<td>无属性的单元格</td>"
    assert _escape_for_json_prompt(raw) == raw


def test_classify_node_html_chunk_prompt_escapes_attribute_quotes(tmp_path):
    """classify_node 传给 LLM 的 prompt 中，HTML 属性双引号应被转义为 \\"."""
    html_content = '<td rowspan="2">取适量试样置于清洁、干燥的白瓷盘中</td>'
    mock_output = ClassifyOutput(segments=[
        SegmentItem(
            content=html_content,
            structure_type="table",
            semantic_type="procedure",
            confidence=0.9,
        ),
    ])

    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch(
        "app.core.parser_workflow.nodes.classify_node.invoke_structured",
        side_effect=capture_invoke,
    ):
        state = _make_state(html_content, tmp_path)
        classify_node(state)

    assert captured_prompts
    prompt = captured_prompts[0]
    assert 'rowspan=\\"2\\"' in prompt, "prompt 中 HTML 属性双引号应已被转义"
    assert 'rowspan="2"' not in prompt, "prompt 中不应含未转义的 HTML 属性双引号"


def test_classify_node_html_chunk_content_unchanged_in_segment(tmp_path):
    """segment.content 应存储原始未转义的 HTML（含真双引号），不得将 \\" 泄漏到存储内容中。

    回归场景（ISSUE-02）：_escape_for_json_prompt 只能作用于 prompt，
    若误将转义结果也写入 segment.content，此测试将捕获该回归。
    """
    html_content = '<td rowspan="2">取适量试样置于清洁、干燥的白瓷盘中</td>'
    # mock LLM 返回原始未转义内容（正确行为：LLM 在 prompt 中看到 \" 后正确还原 "）
    mock_output = ClassifyOutput(segments=[
        SegmentItem(
            content=html_content,
            structure_type="table",
            semantic_type="procedure",
            confidence=0.9,
        ),
    ])

    with patch(
        "app.core.parser_workflow.nodes.classify_node.invoke_structured",
        return_value=mock_output,
    ):
        state = _make_state(html_content, tmp_path)
        result = classify_node(state)

    seg = result["classified_chunks"][0]["segments"][0]
    # 存储的 content 必须包含真双引号（未转义）
    assert '"' in seg["content"], "segment.content 应含真双引号（未转义）"
    # 存储的 content 不应含转义形式 \"
    assert '\\"' not in seg["content"], (
        "segment.content 不应含转义形式 \\\"，_escape_for_json_prompt 只应作用于 prompt"
    )
    # 完整 HTML 属性必须保持原样
    assert 'rowspan="2"' in seg["content"], (
        f'segment.content 中 rowspan="2" 属性丢失或被篡改，实际得到：{seg["content"]!r}'
    )


# ── _merge_formula_with_variables ──────────────────────────────────────────


_CALC_PARAMS = {
    "strategy": "formula_embed",
    "prompt_template": "将以下计算公式及变量说明转化为可检索的混合文本。",
}
_PLAIN_PARAMS = {
    "strategy": "plain_embed",
    "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n",
}


def _formula_seg(content: str) -> TypedSegment:
    return TypedSegment(
        content=content,
        structure_type="formula",
        semantic_type="calculation",
        transform_params=_CALC_PARAMS,
        confidence=0.99,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )


def _var_seg(content: str) -> TypedSegment:
    return TypedSegment(
        content=content,
        structure_type="list",
        semantic_type="calculation",
        transform_params=_CALC_PARAMS,
        confidence=0.98,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )


def _para_seg(content: str) -> TypedSegment:
    return TypedSegment(
        content=content,
        structure_type="paragraph",
        semantic_type="procedure",
        transform_params=_PLAIN_PARAMS,
        confidence=0.95,
        escalated=False,
        cross_refs=[],
        ref_context="",
        failed_table_refs=[],
    )


FORMULA = "$$\nw_{2} = \\frac{m_1 - m_2}{m} \\times 100\\% \\tag{A.2}\n$$"
VARIABLES = "式中：\n\nm₁——坩埚加酸不溶灰分的质量，单位为克 (g)；\nm₂——坩埚的质量，单位为克 (g)；\nm——试样的质量，单位为克 (g)。"


def test_merge_formula_splits_merged_when_separated():
    """公式与变量说明相邻时，应合并为一个 formula segment。"""
    segments = [_formula_seg(FORMULA), _var_seg(VARIABLES)]
    result = _merge_formula_with_variables(segments)

    assert len(result) == 1
    assert result[0]["structure_type"] == "formula"
    assert result[0]["semantic_type"] == "calculation"
    assert FORMULA in result[0]["content"]
    assert VARIABLES in result[0]["content"]


def test_merge_formula_no_change_when_already_merged():
    """公式和变量说明已在同一 segment 时，不应触发合并（数量不变）。"""
    already_merged = _formula_seg(FORMULA + "\n\n" + VARIABLES)
    other = _para_seg("试验结果以平行测定结果的算术平均值为准。")
    segments = [already_merged, other]
    result = _merge_formula_with_variables(segments)

    assert len(result) == 2
    assert result[0]["content"] == already_merged["content"]


def test_merge_formula_two_consecutive_formulas():
    """两个连续公式各自有变量说明时，每对独立合并，互不干扰。"""
    formula_b = "$$\nw_{3} = \\frac{m_1 - m_2 - m_3}{m} \\times 100\\% \\tag{A.3}\n$$"
    variables_b = "式中：\n\nm₁——最终称量的总质量；\nm₂——助滤剂的质量；\nm₃——坩埚的质量。"
    segments = [
        _formula_seg(FORMULA),
        _var_seg(VARIABLES),
        _formula_seg(formula_b),
        _var_seg(variables_b),
    ]
    result = _merge_formula_with_variables(segments)

    assert len(result) == 2
    assert FORMULA in result[0]["content"]
    assert VARIABLES in result[0]["content"]
    assert formula_b in result[1]["content"]
    assert variables_b in result[1]["content"]


def test_merge_formula_skips_non_shizong_calculation_list():
    """紧邻 formula 的 calculation list 若不以"式中"开头，不应合并。"""
    non_var = _var_seg("结果取平行测定的算术平均值。")  # calculation 但不是变量说明
    segments = [_formula_seg(FORMULA), non_var]
    result = _merge_formula_with_variables(segments)

    assert len(result) == 2


def test_merge_formula_preserves_surrounding_segments():
    """合并只影响匹配的相邻对，前后其他 segment 应原样保留。"""
    header = _para_seg("## A.6.4 结果计算")
    footer = _para_seg("试验结果以平行测定结果的算术平均值为准。")
    segments = [header, _formula_seg(FORMULA), _var_seg(VARIABLES), footer]
    result = _merge_formula_with_variables(segments)

    assert len(result) == 3
    assert result[0]["content"] == header["content"]
    assert result[2]["content"] == footer["content"]


# ── _merge_short_segments ──────────────────────────────────────────────────

SHORT = "x" * (_MERGE_SHORT_THRESHOLD - 1)   # 刚好低于阈值
LONG  = "x" * (_MERGE_SHORT_THRESHOLD + 10)  # 高于阈值


def _mat_seg(content: str) -> TypedSegment:
    return TypedSegment(
        content=content, structure_type="list", semantic_type="material",
        transform_params=_PLAIN_PARAMS, confidence=0.9, escalated=False,
        cross_refs=[], ref_context="", failed_table_refs=[],
    )


def _proc_seg(content: str) -> TypedSegment:
    return TypedSegment(
        content=content, structure_type="list", semantic_type="procedure",
        transform_params=_PLAIN_PARAMS, confidence=0.9, escalated=False,
        cross_refs=[], ref_context="", failed_table_refs=[],
    )


def test_merge_short_merges_same_semantic_both_short():
    """两个同 semantic_type 且都短的 segment 应合并为一个。"""
    result = _merge_short_segments([_mat_seg(SHORT), _mat_seg(SHORT)])
    assert len(result) == 1
    assert SHORT in result[0]["content"]


def test_merge_short_short_after_long_merges_in():
    """短 segment 在长 segment 之后时，并入前一个长 segment。"""
    result = _merge_short_segments([_mat_seg(LONG), _mat_seg(SHORT)])
    assert len(result) == 1


def test_merge_short_short_before_long_stays_separate():
    """短 segment 在前、长 segment 在后时，短的无前驱可并入，各自独立。"""
    result = _merge_short_segments([_mat_seg(SHORT), _mat_seg(LONG)])
    assert len(result) == 2


def test_merge_short_no_merge_both_long():
    """两个都超过阈值的 segment 不合并。"""
    result = _merge_short_segments([_mat_seg(LONG), _mat_seg(LONG)])
    assert len(result) == 2


def test_merge_short_no_merge_different_semantic():
    """不同 semantic_type 即使一个很短也不合并。"""
    result = _merge_short_segments([_mat_seg(SHORT), _proc_seg(LONG)])
    assert len(result) == 2


def test_merge_short_cascades_multiple_short():
    """多个连续短 segment 应级联合并为一个。"""
    segs = [_mat_seg(SHORT)] * 5
    result = _merge_short_segments(segs)
    assert len(result) == 1


def test_merge_short_preserves_content():
    """合并后 content 应包含所有原始内容，以换行分隔。"""
    a, b = "4.1 甲砜霉素对照品", "4.2 乙酸乙酯"
    result = _merge_short_segments([_mat_seg(a), _mat_seg(b)])
    assert a in result[0]["content"]
    assert b in result[0]["content"]


def test_merge_short_keeps_first_segment_metadata():
    """合并后保留第一个 segment 的 structure_type / semantic_type。"""
    result = _merge_short_segments([_mat_seg(SHORT), _mat_seg(SHORT)])
    assert result[0]["semantic_type"] == "material"
    assert result[0]["structure_type"] == "list"


def test_merge_short_long_boundary_between_short_groups():
    """长 segment 不触发合并，但其后的短 segment 会并入长 segment。
    [SHORT, SHORT, LONG, SHORT, SHORT] → [SHORT+SHORT, LONG+SHORT+SHORT]
    """
    segs = [_mat_seg(SHORT), _mat_seg(SHORT), _mat_seg(LONG), _mat_seg(SHORT), _mat_seg(SHORT)]
    result = _merge_short_segments(segs)
    assert len(result) == 2
    # 前两个 SHORT 合并为第一组
    assert SHORT in result[0]["content"]
    # LONG 保留，后两个 SHORT 并入
    assert LONG in result[1]["content"]
