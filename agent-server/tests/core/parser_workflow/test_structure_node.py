import pytest
from unittest.mock import patch

from app.core.parser_workflow.models import WorkflowState
from app.core.parser_workflow.nodes.structure_node import (
    match_doc_type_by_rules,
    structure_node,
)


def _make_state(md: str, rules_dir: str = "/tmp") -> WorkflowState:
    return WorkflowState(
        md_content=md,
        doc_metadata={"standard_no": "GB_TEST", "title": "测试"},
        config={},
        rules_dir=rules_dir,
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


DETECTION_MD = """# 乙氧基喹的测定

## 范围

本标准规定乙氧基喹检测方法。

## 试剂和材料

硫酸铵。

## 仪器和设备

分光光度计。

## 分析步骤

操作步骤如下。
"""

SINGLE_ADDITIVE_MD = """# β-胡萝卜素

## 范围

食品添加剂使用标准。

## 技术要求

理化指标见下表。含量不得少于 96%。

## 检验规则

按批次检验。
"""


def test_match_detection_method_by_keywords(tmp_path):
    from app.core.parser_workflow.rules import RulesStore

    store = RulesStore(str(tmp_path))
    doc_type, source = match_doc_type_by_rules(DETECTION_MD, store)
    assert doc_type == "detection_method"
    assert source == "rule"


def test_match_single_additive_by_keywords(tmp_path):
    from app.core.parser_workflow.rules import RulesStore

    store = RulesStore(str(tmp_path))
    doc_type, source = match_doc_type_by_rules(SINGLE_ADDITIVE_MD, store)
    assert doc_type == "single_additive"
    assert source == "rule"


def test_returns_none_when_no_match(tmp_path):
    from app.core.parser_workflow.rules import RulesStore

    store = RulesStore(str(tmp_path))
    md = "## 随机内容\n\n没有任何匹配关键词。"
    result = match_doc_type_by_rules(md, store)
    assert result is None


def test_structure_node_sets_doc_type_in_metadata(tmp_path):
    state = _make_state(SINGLE_ADDITIVE_MD, str(tmp_path))
    result = structure_node(state)
    assert result["doc_metadata"]["doc_type"] == "single_additive"
    assert result["doc_metadata"]["doc_type_source"] == "rule"


def test_structure_node_calls_llm_when_no_rule_match(tmp_path):
    state = _make_state("## 随机内容\n\n无任何关键词匹配", str(tmp_path))
    mock_response = {
        "id": "generic_standard",
        "description": "通用国家标准",
        "detect_keywords": ["范围"],
        "detect_heading_patterns": ["范围"],
        "source": "llm",
    }
    with patch(
        "app.core.parser_workflow.nodes.structure_node._infer_doc_type_with_llm",
        return_value=mock_response,
    ):
        result = structure_node(state)
    assert result["doc_metadata"]["doc_type"] == "generic_standard"
    assert result["doc_metadata"]["doc_type_source"] == "llm"


def test_structure_node_llm_fallback_persists_new_rule_to_disk(tmp_path):
    state = _make_state("## 随机内容\n\n无任何关键词匹配", str(tmp_path))
    mock_response = {
        "id": "new_persisted_type",
        "description": "新文档类型",
        "detect_keywords": ["新关键词"],
        "detect_heading_patterns": [],
        "source": "llm",
    }
    with patch(
        "app.core.parser_workflow.nodes.structure_node._infer_doc_type_with_llm",
        return_value=mock_response,
    ):
        structure_node(state)
    from app.core.parser_workflow.rules import RulesStore

    store = RulesStore(str(tmp_path))
    ids = [d["id"] for d in store.get_doc_type_rules()["doc_types"]]
    assert "new_persisted_type" in ids

