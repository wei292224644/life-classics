from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.parser_workflow.nodes.transform_node import (
    _call_llm_transform,
    apply_strategy,
    transform_node,
)
from app.core.parser_workflow.models import (
    ClassifiedChunk,
    DocumentChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)


# ── _call_llm_transform ──────────────────────────────────────────────


def test_call_llm_transform_returns_content():
    """_call_llm_transform 调用 chat.invoke 后返回 content 字段"""
    mock_resp = MagicMock()
    mock_resp.content = "转化后的文本"

    with patch(
        "app.core.parser_workflow.nodes.transform_node.create_chat_model"
    ) as mock_factory, patch(
        "app.core.parser_workflow.nodes.transform_node.resolve_provider",
        return_value="openai",
    ):
        mock_chat = MagicMock()
        mock_chat.invoke.return_value = mock_resp
        mock_factory.return_value = mock_chat

        result = _call_llm_transform(
            "原始内容",
            {"strategy": "plain_embed", "prompt_template": "请转化以下内容："},
        )

    assert result == "转化后的文本"
    mock_chat.invoke.assert_called_once()


def test_call_llm_transform_uses_correct_provider():
    """_call_llm_transform 通过 resolve_provider 和 create_chat_model 创建 LLM"""
    mock_resp = MagicMock()
    mock_resp.content = "output"

    with patch(
        "app.core.parser_workflow.nodes.transform_node.resolve_provider",
        return_value="dashscope",
    ) as mock_resolve, patch(
        "app.core.parser_workflow.nodes.transform_node.create_chat_model"
    ) as mock_factory, patch(
        "app.core.parser_workflow.nodes.transform_node.settings"
    ) as mock_settings:
        mock_settings.TRANSFORM_LLM_PROVIDER = "dashscope"
        mock_settings.TRANSFORM_MODEL = "qwen-max"
        mock_chat = MagicMock()
        mock_chat.invoke.return_value = mock_resp
        mock_factory.return_value = mock_chat

        _call_llm_transform("内容", {"strategy": "s", "prompt_template": "p"})

    mock_resolve.assert_called_once_with("dashscope")
    mock_factory.assert_called_once()


# ── apply_strategy ───────────────────────────────────────────────────


def test_apply_strategy_returns_document_chunks():
    """apply_strategy 对每个 segment 调用 LLM 转化并返回 DocumentChunk 列表"""
    raw_chunk: RawChunk = {
        "content": "原始文本",
        "section_path": ["1", "1.1"],
        "char_count": 4,
    }
    seg: TypedSegment = {
        "content": "片段内容",
        "content_type": "scope",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "请转化："},
        "confidence": 0.9,
        "escalated": False,
    }
    doc_metadata = {"standard_no": "GB/T-001", "title": "测试标准"}

    with patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="转化结果",
    ):
        result = apply_strategy([seg], raw_chunk, doc_metadata)

    assert len(result) == 1
    chunk = result[0]
    assert chunk["content"] == "转化结果"
    assert chunk["raw_content"] == "原始文本"
    assert chunk["content_type"] == "scope"
    assert chunk["meta"]["transform_strategy"] == "plain_embed"
    assert chunk["meta"]["segment_raw_content"] == "片段内容"


# ── transform_node ───────────────────────────────────────────────────


def test_transform_node_processes_all_chunks():
    """transform_node 处理所有 classified_chunks 并返回 final_chunks"""
    raw_chunk: RawChunk = {
        "content": "原始文本",
        "section_path": ["2"],
        "char_count": 4,
    }
    seg: TypedSegment = {
        "content": "片段",
        "content_type": "definition",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "转化："},
        "confidence": 0.95,
        "escalated": False,
    }
    classified: ClassifiedChunk = {
        "raw_chunk": raw_chunk,
        "segments": [seg],
        "has_unknown": False,
    }
    state: WorkflowState = {
        "md_content": "",
        "rules_dir": "rules",
        "raw_chunks": [],
        "classified_chunks": [classified],
        "doc_metadata": {"standard_no": "GB/T-002"},
        "final_chunks": [],
        "config": {},
        "errors": [],
    }

    with patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="最终文本",
    ):
        result = transform_node(state)

    assert "final_chunks" in result
    assert len(result["final_chunks"]) == 1
    assert result["final_chunks"][0]["content"] == "最终文本"


def test_call_llm_transform_appends_ref_context_to_prompt():
    """ref_context 非空时，prompt 应包含表格内容"""
    mock_resp = MagicMock()
    mock_resp.content = "转化后的文本"
    captured_prompt = {}

    def capture_invoke(prompt):
        captured_prompt["value"] = prompt
        return mock_resp

    with patch(
        "app.core.parser_workflow.nodes.transform_node.create_chat_model"
    ) as mock_factory, patch(
        "app.core.parser_workflow.nodes.transform_node.resolve_provider",
        return_value="openai",
    ):
        mock_chat = MagicMock()
        mock_chat.invoke.side_effect = capture_invoke
        mock_factory.return_value = mock_chat

        _call_llm_transform(
            "样品浓缩条件见表1",
            {"strategy": "semantic_standardization", "prompt_template": "请转化："},
            ref_context="| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        )

    assert "流速" in captured_prompt["value"]
    assert "表格" in captured_prompt["value"]


def test_call_llm_transform_no_ref_context_unchanged():
    """ref_context 为空时，prompt 不包含额外表格内容"""
    mock_resp = MagicMock()
    mock_resp.content = "转化后的文本"
    captured_prompt = {}

    def capture_invoke(prompt):
        captured_prompt["value"] = prompt
        return mock_resp

    with patch(
        "app.core.parser_workflow.nodes.transform_node.create_chat_model"
    ) as mock_factory, patch(
        "app.core.parser_workflow.nodes.transform_node.resolve_provider",
        return_value="openai",
    ):
        mock_chat = MagicMock()
        mock_chat.invoke.side_effect = capture_invoke
        mock_factory.return_value = mock_chat

        _call_llm_transform(
            "普通内容",
            {"strategy": "plain_embed", "prompt_template": "请转化："},
        )

    assert "表格" not in captured_prompt["value"]


def test_apply_strategy_writes_cross_refs_to_meta():
    """apply_strategy 应将 seg 的 cross_refs 写入 DocumentChunk.meta"""
    raw_chunk: RawChunk = {
        "content": "原始文本",
        "section_path": ["1", "1.1"],
        "char_count": 4,
    }
    seg: TypedSegment = {
        "content": "片段内容",
        "content_type": "plain_text",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "请转化："},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": ["表1", "图A.1"],
        "ref_context": "| 参数 | 值 |",
        "failed_table_refs": [],
    }
    doc_metadata = {"standard_no": "GB/T-001", "title": "测试标准"}

    with patch(
        "app.core.parser_workflow.nodes.transform_node._call_llm_transform",
        return_value="转化结果",
    ):
        result = apply_strategy([seg], raw_chunk, doc_metadata)

    assert result[0]["meta"]["cross_refs"] == ["表1", "图A.1"]
    assert "failed_table_refs" in result[0]["meta"]
