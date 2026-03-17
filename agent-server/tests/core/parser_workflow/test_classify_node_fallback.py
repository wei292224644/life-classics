from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from app.core.parser_workflow.nodes.classify_node import _call_classify_llm, classify_raw_chunk
from app.core.parser_workflow.models import RawChunk
from app.core.parser_workflow.nodes.output import ClassifyOutput, SegmentItem
from app.core.parser_workflow.structured_llm import StructuredOutputError


def test_invoke_structured_fails_raises_structured_output_error():
    """invoke_structured 失败时应抛出 StructuredOutputError（fail-fast）。"""
    content_types = [{"id": "preface", "description": "前言"}]
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
        "app.core.parser_workflow.nodes.classify_node.invoke_structured",
        side_effect=err,
    ):
        with pytest.raises(StructuredOutputError) as exc_info:
            _call_classify_llm("前言", content_types)

        assert exc_info.value.node_name == "classify_node"
        assert exc_info.value.response_model == "ClassifyOutput"


def test_invoke_structured_succeeds_returns_segments():
    """invoke_structured 成功时返回 segments。"""
    content_types = [{"id": "preface", "description": "前言"}]
    expected = ClassifyOutput(
        segments=[
            SegmentItem(content="前言内容", content_type="preface", confidence=0.93)
        ]
    )

    with patch(
        "app.core.parser_workflow.nodes.classify_node.invoke_structured",
        return_value=expected,
    ):
        segments = _call_classify_llm("前言", content_types)

    assert len(segments) == 1
    assert segments[0].content == "前言内容"
    assert segments[0].content_type == "preface"
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
        "content_types": [{"id": "preface", "description": "前言"}]
    }
    store.get_transform_params.return_value = {
        "strategy": "plain_embed",
        "prompt_template": "请转化",
    }

    with patch(
        "app.core.parser_workflow.nodes.classify_node._call_classify_llm",
        return_value=[
            SegmentItem(content="低置信片段", content_type="preface", confidence=0.5),
            SegmentItem(content="高置信片段", content_type="preface", confidence=0.9),
        ],
    ):
        out = classify_raw_chunk(raw_chunk, store)

    assert out["has_unknown"] is True
    assert len(out["segments"]) == 2
    assert out["segments"][0]["content_type"] == "unknown"
    assert out["segments"][1]["content_type"] == "preface"
