from unittest.mock import patch
import pytest

from app.core.parser_workflow.models import RawChunk, WorkflowState
from app.core.parser_workflow.nodes.classify_node import classify_node
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
