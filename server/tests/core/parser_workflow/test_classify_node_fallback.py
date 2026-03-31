from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from worflow_parser_kb.nodes.classify_node import _call_classify_llm, classify_raw_chunk
from worflow_parser_kb.models import RawChunk
from worflow_parser_kb.nodes.output import ClassifyOutput, SegmentItem
from worflow_parser_kb.structured_llm.errors import StructuredOutputError


def test_invoke_structured_fails_raises_structured_output_error():
    """invoke_structured 失败时应抛出 StructuredOutputError（fail-fast）。"""
    structure_types = [{"id": "paragraph", "description": "叙述性段落"}]
    semantic_types = [{"id": "scope", "description": "适用范围"}]
    err = StructuredOutputError(
        "结构化输出校验失败: classify_node",
        provider="openai",
        model="gpt-4o-mini",
        node_name="classify_node",
        response_model="ClassifyOutput",
        retry_count=0,
        raw_error="validation error",
    )

    with patch(
        "worflow_parser_kb.nodes.classify_node.invoke_structured",
        side_effect=err,
    ):
        with pytest.raises(StructuredOutputError) as exc_info:
            _call_classify_llm("前言", structure_types, semantic_types)

        assert exc_info.value.node_name == "classify_node"
        assert exc_info.value.response_model == "ClassifyOutput"


def test_invoke_structured_succeeds_returns_segments():
    """invoke_structured 成功时返回 segments。"""
    structure_types = [{"id": "list", "description": "编号列表"}]
    semantic_types = [{"id": "procedure", "description": "操作步骤"}]
    expected = ClassifyOutput(
        segments=[
            SegmentItem(content="前言内容", structure_type="list", semantic_type="procedure", confidence=0.93)
        ]
    )

    with patch(
        "worflow_parser_kb.nodes.classify_node.invoke_structured",
        return_value=expected,
    ):
        segments = _call_classify_llm("前言", structure_types, semantic_types)

    assert len(segments) == 1
    assert segments[0].content == "前言内容"
    assert segments[0].structure_type == "list"
    assert segments[0].semantic_type == "procedure"
    assert segments[0].confidence == 0.93


def test_classify_raw_chunk_builds_typed_segments_with_threshold():
    """classify_raw_chunk 应按阈值生成 known/unknown 的 TypedSegment。"""
    raw_chunk: RawChunk = {
        "content": "测试文本",
        "section_path": ["前言"],
        "char_count": 4,
    }
    store = MagicMock()
    store.get_confidence_threshold.return_value = 0.7
    store.get_content_type_rules.return_value = {
        "structure_types": [{"id": "paragraph", "description": "叙述性段落"}],
        "semantic_types": [{"id": "scope", "description": "适用范围"}],
    }
    store.get_transform_params.return_value = {
        "strategy": "plain_embed",
        "prompt_template": "请转化",
    }

    with patch(
        "worflow_parser_kb.nodes.classify_node._call_classify_llm",
        return_value=[
            SegmentItem(content="低置信片段", structure_type="paragraph", semantic_type="scope", confidence=0.5),
            SegmentItem(content="高置信片段", structure_type="list", semantic_type="procedure", confidence=0.9),
        ],
    ):
        out = classify_raw_chunk(raw_chunk, store)

    assert out["has_unknown"] is True
    assert len(out["segments"]) == 2
    assert out["segments"][0]["structure_type"] == "unknown"
    assert out["segments"][0]["semantic_type"] == "unknown"
    assert out["segments"][1]["structure_type"] == "list"
    assert out["segments"][1]["semantic_type"] == "procedure"
