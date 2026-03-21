from __future__ import annotations

from unittest.mock import patch

import pytest

from parser.structured_llm import StructuredOutputError
from parser.nodes.transform_node import (
    _call_llm_transform,
    apply_strategy,
    transform_node,
)
from parser.models import (
    ClassifiedChunk,
    DocumentChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)


# ── _call_llm_transform ──────────────────────────────────────────────


def test_call_llm_transform_returns_content():
    """_call_llm_transform 调用 invoke_structured 后返回 content 字段"""
    from parser.nodes.output import TransformOutput

    mock_resp = TransformOutput(content="转化后的文本")

    with patch(
        "parser.nodes.transform_node.invoke_structured",
        return_value=mock_resp,
    ) as mock_invoke:
        result = _call_llm_transform(
            "原始内容",
            {"strategy": "plain_embed", "prompt_template": "请转化以下内容："},
        )

    assert result == "转化后的文本"
    mock_invoke.assert_called_once()


def test_call_llm_transform_uses_invoke_structured():
    """_call_llm_transform 通过 invoke_structured 调用 LLM"""
    from parser.nodes.output import TransformOutput

    mock_resp = TransformOutput(content="output")

    with patch(
        "parser.nodes.transform_node.invoke_structured",
        return_value=mock_resp,
    ) as mock_invoke:
        _call_llm_transform("内容", {"strategy": "s", "prompt_template": "p"})

    mock_invoke.assert_called_once()
    call_kwargs = mock_invoke.call_args.kwargs
    assert call_kwargs["node_name"] == "transform_node"
    assert call_kwargs["response_model"].__name__ == "TransformOutput"


def test_call_llm_transform_invoke_structured_fails_raises():
    """invoke_structured 失败时应上抛 StructuredOutputError（fail-fast）。"""
    err = StructuredOutputError(
        "结构化输出调用失败（不可恢复错误）: transform_node",
        provider="openai",
        model="qwen-max",
        node_name="transform_node",
        response_model="TransformOutput",
        retry_count=0,
        raw_error="validation error",
    )
    with patch(
        "parser.nodes.transform_node.invoke_structured",
        side_effect=err,
    ):
        with pytest.raises(StructuredOutputError) as exc_info:
            _call_llm_transform(
                "内容",
                {"strategy": "plain_embed", "prompt_template": "请转化："},
            )
    assert exc_info.value.node_name == "transform_node"


# ── apply_strategy ───────────────────────────────────────────────────


def test_apply_strategy_returns_document_chunks():
    """apply_strategy 对每个 segment 调用 LLM 转化并返回 DocumentChunk 列表"""
    raw_chunk: RawChunk = {
        "content": "原始文本",
        "section_path": ["1", "1.1"],
        "char_count": 4,
    }
    seg: TypedSegment = {
        "content": "称取试料（5 ± 0.05）g，于50 mL离心管中，加乙酸乙酯20 mL，振荡10 min，4000 r/min离心。",
        "structure_type": "paragraph",
        "semantic_type": "scope",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "请转化："},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    doc_metadata = {"standard_no": "GB/T-001", "title": "测试标准"}

    with patch(
        "parser.nodes.transform_node._call_llm_transform",
        return_value="转化结果",
    ):
        result = apply_strategy([seg], raw_chunk, doc_metadata)

    assert len(result) == 1
    chunk = result[0]
    assert chunk["content"] == "转化结果"
    assert chunk["raw_content"] == "称取试料（5 ± 0.05）g，于50 mL离心管中，加乙酸乙酯20 mL，振荡10 min，4000 r/min离心。"
    assert chunk["structure_type"] == "paragraph"
    assert chunk["semantic_type"] == "scope"
    assert chunk["meta"]["transform_strategy"] == "plain_embed"
    assert chunk["meta"]["segment_raw_content"] == "称取试料（5 ± 0.05）g，于50 mL离心管中，加乙酸乙酯20 mL，振荡10 min，4000 r/min离心。"


# ── transform_node ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transform_node_processes_all_chunks():
    """transform_node 处理所有 classified_chunks 并返回 final_chunks"""
    raw_chunk: RawChunk = {
        "content": "原始文本",
        "section_path": ["2"],
        "char_count": 4,
    }
    seg: TypedSegment = {
        "content": "本标准中甲砜霉素是指氯霉素类广谱抗生素，化学名为甲砜氯霉素，主要用于细菌感染治疗，牛奶中残留量需符合国家限量标准。",
        "structure_type": "paragraph",
        "semantic_type": "definition",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "转化："},
        "confidence": 0.95,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
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
        "parser.nodes.transform_node._call_llm_transform",
        return_value="最终文本",
    ):
        result = await transform_node(state)

    assert "final_chunks" in result
    assert len(result["final_chunks"]) == 1
    assert result["final_chunks"][0]["content"] == "最终文本"


def test_call_llm_transform_appends_ref_context_to_prompt():
    """ref_context 非空时，prompt 应包含表格内容"""
    from parser.nodes.output import TransformOutput

    mock_resp = TransformOutput(content="转化后的文本")
    captured_prompt = {}

    def capture_invoke(*, prompt, **kwargs):
        captured_prompt["value"] = prompt
        return mock_resp

    with patch(
        "parser.nodes.transform_node.invoke_structured",
        side_effect=capture_invoke,
    ):
        _call_llm_transform(
            "样品浓缩条件见表1",
            {"strategy": "semantic_standardization", "prompt_template": "请转化："},
            ref_context="| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        )

    assert "流速" in captured_prompt["value"]
    assert "表格" in captured_prompt["value"]


def test_call_llm_transform_no_ref_context_unchanged():
    """ref_context 为空时，prompt 不包含额外表格内容"""
    from parser.nodes.output import TransformOutput

    mock_resp = TransformOutput(content="转化后的文本")
    captured_prompt = {}

    def capture_invoke(*, prompt, **kwargs):
        captured_prompt["value"] = prompt
        return mock_resp

    with patch(
        "parser.nodes.transform_node.invoke_structured",
        side_effect=capture_invoke,
    ):
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
        "content": "称取试料（5 ± 0.05）g，于50 mL离心管中，加乙酸乙酯20 mL，振荡10 min，4000 r/min离心。",
        "structure_type": "list",
        "semantic_type": "procedure",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "请转化："},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": ["表1", "图A.1"],
        "ref_context": "| 参数 | 值 |",
        "failed_table_refs": [],
    }
    doc_metadata = {"standard_no": "GB/T-001", "title": "测试标准"}

    with patch(
        "parser.nodes.transform_node._call_llm_transform",
        return_value="转化结果",
    ):
        result = apply_strategy([seg], raw_chunk, doc_metadata)

    assert result[0]["meta"]["cross_refs"] == ["表1", "图A.1"]
    assert "failed_table_refs" in result[0]["meta"]
