from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from worflow_parser_kb.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from worflow_parser_kb.nodes.escalate_node import (
    _call_escalate_llm,
    escalate_node,
)
from worflow_parser_kb.nodes.output import EscalateOutput, TransformParams
from worflow_parser_kb.structured_llm.errors import StructuredOutputError


# ── _call_escalate_llm ───────────────────────────────────────────────────


def test_call_escalate_llm_use_existing_returns_output():
    """use_existing 时返回 EscalateOutput，id 为已有类型"""
    content_types = [{"id": "plain_text", "description": "普通说明性段落"}]
    expected = EscalateOutput(
        action="use_existing",
        id="plain_text",
        description="普通说明性段落",
        transform=TransformParams(
            strategy="semantic_standardization",
            prompt_template="请转化：",
        ),
    )

    with patch(
        "worflow_parser_kb.nodes.escalate_node.invoke_structured",
        return_value=expected,
    ):
        result = _call_escalate_llm("某段说明文字", content_types)

    assert result.action == "use_existing"
    assert result.id == "plain_text"


def test_call_escalate_llm_create_new_returns_output():
    """create_new 时返回 EscalateOutput，含新类型 id 与 transform"""
    content_types = [{"id": "plain_text", "description": "普通说明"}]
    expected = EscalateOutput(
        action="create_new",
        id="custom_section",
        description="自定义章节类型",
        transform=TransformParams(
            strategy="plain_embed",
            prompt_template="请将以下内容转化为规范化的陈述文本：\n",
        ),
    )

    with patch(
        "worflow_parser_kb.nodes.escalate_node.invoke_structured",
        return_value=expected,
    ):
        result = _call_escalate_llm("特殊格式内容", content_types)

    assert result.action == "create_new"
    assert result.id == "custom_section"
    assert result.transform.strategy == "plain_embed"


def test_call_escalate_llm_invoke_structured_fails_raises():
    """invoke_structured 失败时抛出 StructuredOutputError"""
    err = StructuredOutputError(
        "结构化输出校验失败: escalate_node",
        provider="openai",
        model="gpt-4o-mini",
        node_name="escalate_node",
        response_model="EscalateOutput",
        retry_count=0,
        raw_error="validation error",
    )

    with patch(
        "worflow_parser_kb.nodes.escalate_node.invoke_structured",
        side_effect=err,
    ):
        with pytest.raises(StructuredOutputError) as exc_info:
            _call_escalate_llm("内容", [])

        assert exc_info.value.node_name == "escalate_node"


# ── escalate_node ──────────────────────────────────────────────────────


def test_escalate_node_use_existing_no_append():
    """use_existing 时不调用 append_content_type"""
    raw_chunk: RawChunk = {
        "content": "原始文本",
        "section_path": ["1"],
        "char_count": 4,
    }
    seg: TypedSegment = {
        "content": "说明性段落",
        "content_type": "unknown",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "请转化："},
        "confidence": 0.5,
        "escalated": False,
    }
    classified: ClassifiedChunk = {
        "raw_chunk": raw_chunk,
        "segments": [seg],
        "has_unknown": True,
    }
    state: WorkflowState = {
        "md_content": "",
        "rules_dir": "rules",
        "raw_chunks": [],
        "classified_chunks": [classified],
        "doc_metadata": {},
        "final_chunks": [],
        "config": {},
        "errors": [],
    }

    llm_result = EscalateOutput(
        action="use_existing",
        id="plain_text",
        description="普通说明",
        transform=TransformParams(strategy="s", prompt_template="p"),
    )

    with patch(
        "worflow_parser_kb.nodes.escalate_node.invoke_structured",
        return_value=llm_result,
    ), patch(
        "worflow_parser_kb.nodes.escalate_node.RulesStore"
    ) as mock_store_cls:
        mock_store = MagicMock()
        mock_store.get_content_type_rules.return_value = {
            "content_types": [{"id": "plain_text", "description": "普通说明"}]
        }
        mock_store_cls.return_value = mock_store

        result = escalate_node(state)

    mock_store.append_content_type.assert_not_called()
    assert result["classified_chunks"][0]["segments"][0]["content_type"] == "plain_text"
    assert result["classified_chunks"][0]["has_unknown"] is False


def test_escalate_node_create_new_appends_content_type():
    """create_new 时调用 append_content_type 并回写 TypedSegment"""
    raw_chunk: RawChunk = {
        "content": "原始文本",
        "section_path": ["1"],
        "char_count": 4,
    }
    seg: TypedSegment = {
        "content": "特殊内容",
        "content_type": "unknown",
        "transform_params": {"strategy": "plain_embed", "prompt_template": "请转化："},
        "confidence": 0.5,
        "escalated": False,
    }
    classified: ClassifiedChunk = {
        "raw_chunk": raw_chunk,
        "segments": [seg],
        "has_unknown": True,
    }
    state: WorkflowState = {
        "md_content": "",
        "rules_dir": "rules",
        "raw_chunks": [],
        "classified_chunks": [classified],
        "doc_metadata": {},
        "final_chunks": [],
        "config": {},
        "errors": [],
    }

    llm_result = EscalateOutput(
        action="create_new",
        id="new_custom_type",
        description="新自定义类型",
        transform=TransformParams(
            strategy="plain_embed",
            prompt_template="请转化：\n",
        ),
    )

    with patch(
        "worflow_parser_kb.nodes.escalate_node.invoke_structured",
        return_value=llm_result,
    ), patch(
        "worflow_parser_kb.nodes.escalate_node.RulesStore"
    ) as mock_store_cls:
        mock_store = MagicMock()
        mock_store.get_content_type_rules.return_value = {"content_types": []}
        mock_store_cls.return_value = mock_store

        result = escalate_node(state)

    mock_store.append_content_type.assert_called_once()
    call_arg = mock_store.append_content_type.call_args[0][0]
    assert call_arg["id"] == "new_custom_type"
    assert call_arg["action"] == "create_new"
    assert result["classified_chunks"][0]["segments"][0]["content_type"] == "new_custom_type"
    assert result["classified_chunks"][0]["segments"][0]["escalated"] is True
