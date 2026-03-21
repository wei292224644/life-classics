import asyncio

import pytest
from unittest.mock import patch

from parser.models import RawChunk, WorkflowState
from parser.nodes.classify_node import (
    classify_node,
    _escape_for_json_prompt,
    _replace_latex_with_placeholders,
    _restore_placeholders,
)
from parser.nodes.output import ClassifyOutput, SegmentItem


def _make_state(content: str, tmp_path) -> WorkflowState:
    from parser.rules import RulesStore
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


@pytest.mark.asyncio
async def test_classify_node_produces_dual_type_segments(tmp_path):
    """classify_node 应产生含 structure_type + semantic_type 的 segments"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="称取试样约2g", structure_type="list", semantic_type="procedure", confidence=0.9),
    ])

    with patch("parser.nodes.classify_node.invoke_structured", return_value=mock_output):
        state = _make_state("称取试样约2g", tmp_path)
        result = await classify_node(state)

    chunks = result["classified_chunks"]
    assert chunks
    seg = chunks[0]["segments"][0]
    assert seg["structure_type"] == "list"
    assert seg["semantic_type"] == "procedure"
    assert "content_type" not in seg


@pytest.mark.asyncio
async def test_classify_node_low_confidence_sets_unknown(tmp_path):
    """置信度低于阈值时，两个字段均应为 'unknown'"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="某段内容", structure_type="paragraph", semantic_type="scope", confidence=0.3),
    ])

    with patch("parser.nodes.classify_node.invoke_structured", return_value=mock_output):
        state = _make_state("某段内容", tmp_path)
        result = await classify_node(state)

    seg = result["classified_chunks"][0]["segments"][0]
    assert seg["structure_type"] == "unknown"
    assert seg["semantic_type"] == "unknown"
    assert result["classified_chunks"][0]["has_unknown"] is True


@pytest.mark.asyncio
async def test_classify_node_prompt_includes_both_type_lists(tmp_path):
    """LLM 调用的 prompt 应包含 structure_types 和 semantic_types 两组描述"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="x", structure_type="paragraph", semantic_type="scope", confidence=0.9),
    ])

    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch("parser.nodes.classify_node.invoke_structured", side_effect=capture_invoke):
        state = _make_state("x", tmp_path)
        await classify_node(state)

    assert captured_prompts
    prompt = captured_prompts[0]
    for type_id in ["paragraph", "list", "table", "formula", "header"]:
        assert type_id in prompt, f"prompt 未包含 structure_type '{type_id}'"
    for type_id in ["metadata", "scope", "limit", "procedure", "material", "calculation", "definition", "amendment"]:
        assert type_id in prompt, f"prompt 未包含 semantic_type '{type_id}'"


@pytest.mark.asyncio
async def test_classify_node_prompt_contains_formula_rule(tmp_path):
    """prompt 中应包含公式识别确定性规则，要求含 $$ 的 segment 必须分类为 formula"""
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="x", structure_type="formula", semantic_type="calculation", confidence=0.9),
    ])

    captured_prompts = []

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    with patch("parser.nodes.classify_node.invoke_structured", side_effect=capture_invoke):
        state = _make_state("x", tmp_path)
        await classify_node(state)

    prompt = captured_prompts[0]
    assert "$$" in prompt, "prompt 未包含 $$ 公式规则"
    assert "structure_type=formula" in prompt, "prompt 未要求含 $$ 的 segment 用 structure_type=formula"
    assert "semantic_type=calculation" in prompt, "prompt 未要求含 $$ 的 segment 用 semantic_type=calculation"


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


@pytest.mark.asyncio
async def test_classify_node_html_chunk_prompt_escapes_attribute_quotes(tmp_path):
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
        "parser.nodes.classify_node.invoke_structured",
        side_effect=capture_invoke,
    ):
        state = _make_state(html_content, tmp_path)
        await classify_node(state)

    assert captured_prompts
    prompt = captured_prompts[0]
    assert 'rowspan=\\"2\\"' in prompt, "prompt 中 HTML 属性双引号应已被转义"
    assert 'rowspan="2"' not in prompt, "prompt 中不应含未转义的 HTML 属性双引号"


@pytest.mark.asyncio
async def test_classify_node_html_chunk_content_unchanged_in_segment(tmp_path):
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
        "parser.nodes.classify_node.invoke_structured",
        return_value=mock_output,
    ):
        state = _make_state(html_content, tmp_path)
        result = await classify_node(state)

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


@pytest.mark.asyncio
async def test_classify_node_applies_all_hooks(tmp_path):
    """classify_node 应通过 POST_CLASSIFY_HOOKS 注册表应用所有 hook。

    回归测试：确保重构后 hook 仍被执行（以 merge_formula_with_variables 为例）。
    公式 segment 后紧跟"式中..."时，最终应合并为一个 segment。
    """
    formula_content = "$$\nX = C \\times V / m\n$$"
    var_content = "式中：\n\nX——残留量；\nC——浓度；\nV——体积；\nm——质量。"

    mock_output = ClassifyOutput(segments=[
        SegmentItem(
            content=formula_content,
            structure_type="formula",
            semantic_type="calculation",
            confidence=0.99,
        ),
        SegmentItem(
            content=var_content,
            structure_type="list",
            semantic_type="calculation",
            confidence=0.98,
        ),
    ])

    with patch(
        "parser.nodes.classify_node.invoke_structured",
        return_value=mock_output,
    ):
        state = _make_state(formula_content + "\n\n" + var_content, tmp_path)
        result = await classify_node(state)

    segments = result["classified_chunks"][0]["segments"]
    assert len(segments) == 1, "公式与变量说明应已合并为一个 segment"
    assert segments[0]["structure_type"] == "formula"


# ── 占位符预处理 ──────────────────────────────────────────────

def test_replace_inline_latex_single():
    """单个内联公式应被替换为 [__MATH_0__]，mapping 记录原始 LaTeX。"""
    text = "称取 $4\\mathrm{g}$ 试样"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert "[__MATH_0__]" in clean
    assert "$" not in clean
    assert mapping["[__MATH_0__]"] == "$4\\mathrm{g}$"


def test_replace_inline_latex_multiple():
    """多个内联公式按出现顺序分配序号。"""
    text = "加 $200~\\mathrm{mL}$ 水，加热至 $80^{\\circ}C$"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert "[__MATH_0__]" in clean
    assert "[__MATH_1__]" in clean
    assert "$" not in clean
    assert len(mapping) == 2


def test_replace_block_latex():
    """block 公式 $$...$$ 应被替换，且优先于 inline 匹配。"""
    text = "按下式计算：\n$$\nw = m_1 / m\n$$\n式中 w 为质量分数。"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert "[__MATH_0__]" in clean
    assert "$$" not in clean
    assert mapping["[__MATH_0__]"].startswith("$$")


def test_replace_mixed_block_and_inline():
    """block 先替换，inline 后替换，序号连续。"""
    text = "公式：\n$$\nX = a + b\n$$\n其中 $a$ 为常数。"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert len(mapping) == 2
    # block 应为 MATH_0
    assert mapping["[__MATH_0__]"].startswith("$$")
    # inline 应为 MATH_1
    assert mapping["[__MATH_1__]"] == "$a$"


def test_replace_no_latex_unchanged():
    """不含 LaTeX 的文本应原样返回，mapping 为空。"""
    text = "本标准适用于食品添加剂卡拉胶。"
    clean, mapping = _replace_latex_with_placeholders(text)
    assert clean == text
    assert mapping == {}


# ── 占位符后处理 ──────────────────────────────────────────────

def test_restore_placeholders_normal():
    """正常情况下占位符应被精确还原为原始 LaTeX。"""
    mapping = {"[__MATH_0__]": "$4\\mathrm{g}$"}
    text = "称取 [__MATH_0__] 试样"
    result = _restore_placeholders(text, mapping)
    assert result == "称取 $4\\mathrm{g}$ 试样"


def test_restore_placeholders_tolerates_extra_spaces():
    """占位符前后多余空格应被容忍，还原后得到完整原始 LaTeX。"""
    mapping = {"[__MATH_0__]": "$4\\mathrm{g}$"}
    text = "称取 [ __MATH_0__ ] 试样"
    result = _restore_placeholders(text, mapping)
    assert result == "称取 $4\\mathrm{g}$ 试样"


def test_restore_placeholders_missing_not_raises():
    """若 LLM 删除了占位符，不抛异常，返回原文本。"""
    mapping = {"[__MATH_0__]": "$4\\mathrm{g}$"}
    text = "称取试样"
    result = _restore_placeholders(text, mapping)
    assert result == "称取试样"


def test_restore_placeholders_multiple():
    """多个占位符全部还原。"""
    mapping = {
        "[__MATH_0__]": "$200~\\mathrm{mL}$",
        "[__MATH_1__]": "$80^{\\circ}C$",
    }
    text = "加 [__MATH_0__] 水，加热至 [__MATH_1__]"
    result = _restore_placeholders(text, mapping)
    assert result == "加 $200~\\mathrm{mL}$ 水，加热至 $80^{\\circ}C$"


# ── 占位符集成测试 ──────────────────────────────────────────────

def test_classify_llm_sends_placeholder_not_latex(tmp_path):
    """_call_classify_llm 发给 LLM 的 prompt 应含占位符而非原始 LaTeX。"""
    from parser.nodes.classify_node import _call_classify_llm
    from parser.rules import RulesStore

    captured_prompts = []
    mock_output = ClassifyOutput(segments=[
        SegmentItem(content="[__MATH_0__]", structure_type="formula", semantic_type="calculation", confidence=0.95),
    ])

    def capture_invoke(node_name, prompt, response_model, **kwargs):
        captured_prompts.append(prompt)
        return mock_output

    store = RulesStore(str(tmp_path))
    ct_rules = store.get_content_type_rules()
    structure_types = ct_rules.get("structure_types", [])
    semantic_types = ct_rules.get("semantic_types", [])

    with patch("parser.nodes.classify_node.invoke_structured", side_effect=capture_invoke):
        _call_classify_llm(
            "称取 $4\\mathrm{g}$ 试样",
            structure_types,
            semantic_types,
        )

    assert captured_prompts
    prompt = captured_prompts[0]
    assert "[__MATH_0__]" in prompt, "prompt 中应含占位符"
    assert "$4\\mathrm{g}$" not in prompt, "prompt 中不应含原始 LaTeX"


@pytest.mark.asyncio
async def test_classify_node_restores_latex_in_seg_content(tmp_path):
    """classify_node 输出的 segment.content 应含还原后的原始 LaTeX。"""
    latex_text = "称取 $4\\mathrm{g}$ 试样，加热至 $80^{\\circ}C$。"
    mock_output = ClassifyOutput(segments=[
        SegmentItem(
            content="称取 [__MATH_0__] 试样，加热至 [__MATH_1__]。",
            structure_type="procedure",
            semantic_type="procedure",
            confidence=0.9,
        ),
    ])

    with patch("parser.nodes.classify_node.invoke_structured", return_value=mock_output):
        state = _make_state(latex_text, tmp_path)
        result = await classify_node(state)

    seg = result["classified_chunks"][0]["segments"][0]
    assert "$4\\mathrm{g}$" in seg["content"], "原始 LaTeX 应已还原到 segment.content"
    assert "$80^{\\circ}C$" in seg["content"], "原始 LaTeX 应已还原到 segment.content"
    assert "[__MATH_0__]" not in seg["content"], "占位符不应出现在最终 segment.content 中"
