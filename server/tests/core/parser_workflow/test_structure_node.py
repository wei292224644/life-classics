from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from worflow_parser_kb.structured_llm.errors import StructuredOutputError
from worflow_parser_kb.nodes.structure_node import (
    _infer_doc_type_with_llm,
    match_doc_type_by_rules,
    structure_node,
)
from worflow_parser_kb.models import WorkflowState


# ── _infer_doc_type_with_llm ─────────────────────────────────────────


def test_infer_doc_type_with_llm_calls_invoke_structured():
    """验证 invoke_structured 被正确调用并返回 DocTypeOutput"""
    from worflow_parser_kb.nodes.output import DocTypeOutput

    mock_output = DocTypeOutput(
        id="additive_standard",
        description="食品添加剂标准",
        detect_keywords=["添加剂"],
        detect_heading_patterns=["食品添加剂"],
    )

    with patch(
        "worflow_parser_kb.nodes.structure_node.invoke_structured",
        return_value=mock_output,
    ) as mock_invoke:
        result = _infer_doc_type_with_llm(
            ["范围", "食品添加剂的使用"],
            [{"id": "existing_type", "description": "已有类型"}],
            {},
        )

    mock_invoke.assert_called_once()
    call_kwargs = mock_invoke.call_args.kwargs
    assert call_kwargs["node_name"] == "structure_node"
    assert call_kwargs["response_model"].__name__ == "DocTypeOutput"
    assert result["id"] == "additive_standard"


def test_infer_doc_type_with_llm_raises_on_structured_error():
    """invoke_structured 失败时应上抛 StructuredOutputError（fail-fast）。"""
    err = StructuredOutputError(
        "结构化输出校验失败: structure_node",
        provider="openai",
        model="qwen-max",
        node_name="structure_node",
        response_model="DocTypeOutput",
        retry_count=0,
        raw_error="validation error",
    )
    with patch(
        "worflow_parser_kb.nodes.structure_node.invoke_structured",
        side_effect=err,
    ):
        with pytest.raises(StructuredOutputError) as exc_info:
            _infer_doc_type_with_llm(
                ["范围", "食品添加剂的使用"],
                [{"id": "existing_type", "description": "已有类型"}],
                {},
            )
    assert exc_info.value.node_name == "structure_node"


# ── match_doc_type_by_rules ──────────────────────────────────────────


def test_structure_node_uses_rule_match():
    """验证规则匹配成功时不调用 LLM"""
    mock_store = MagicMock()
    mock_store.get_doc_type_rules.return_value = {
        "match_threshold": 1,
        "doc_types": [
            {
                "id": "pesticide_residue",
                "description": "农药残留标准",
                "detect_keywords": ["农药残留"],
                "detect_heading_patterns": ["农药残留限量"],
            }
        ],
    }

    state: WorkflowState = {
        "md_content": "## 农药残留限量\n本标准规定了农药残留的限量要求。",
        "rules_dir": "fake/rules/dir",
        "raw_chunks": [],
        "classified_chunks": [],
        "doc_metadata": {"standard_no": "GB 2763"},
        "final_chunks": [],
        "config": {},
        "errors": [],
    }

    with patch(
        "worflow_parser_kb.nodes.structure_node.RulesStore",
        return_value=mock_store,
    ), patch(
        "worflow_parser_kb.nodes.structure_node._infer_doc_type_with_llm"
    ) as mock_llm:
        result = structure_node(state)

    mock_llm.assert_not_called()
    assert result["doc_metadata"]["doc_type"] == "pesticide_residue"
    assert result["doc_metadata"]["doc_type_source"] == "rule"


def test_structure_node_falls_back_to_llm():
    """验证规则匹配失败时调用 LLM 并保存新规则"""
    mock_store = MagicMock()
    mock_store.get_doc_type_rules.return_value = {
        "match_threshold": 2,
        "doc_types": [],
    }

    new_rule = {
        "id": "new_inferred_type",
        "description": "推断出的新类型",
        "detect_keywords": ["关键词"],
        "detect_heading_patterns": ["标题模式"],
    }

    state: WorkflowState = {
        "md_content": "## 范围\n本标准适用于某类特殊食品。",
        "rules_dir": "fake/rules/dir",
        "raw_chunks": [],
        "classified_chunks": [],
        "doc_metadata": {"standard_no": "GB 99999"},
        "final_chunks": [],
        "config": {},
        "errors": [],
    }

    with patch(
        "worflow_parser_kb.nodes.structure_node.RulesStore",
        return_value=mock_store,
    ), patch(
        "worflow_parser_kb.nodes.structure_node._infer_doc_type_with_llm",
        return_value=new_rule,
    ) as mock_llm:
        result = structure_node(state)

    mock_llm.assert_called_once()
    mock_store.append_doc_type.assert_called_once_with(new_rule)
    assert result["doc_metadata"]["doc_type"] == "new_inferred_type"
    assert result["doc_metadata"]["doc_type_source"] == "llm"
