import pytest

from app.core.parser_workflow.nodes.parse_node import parse_node
from app.core.parser_workflow.models import WorkflowState


def _make_state(md: str, meta: dict) -> WorkflowState:
    return WorkflowState(
        md_content=md,
        doc_metadata=meta,
        config={},
        rules_dir="/tmp",
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


def test_passes_through_provided_metadata():
    state = _make_state("## 范围\n内容", {"standard_no": "GB2760", "title": "食品添加剂"})
    result = parse_node(state)
    assert result["doc_metadata"]["standard_no"] == "GB2760"
    assert result["doc_metadata"]["title"] == "食品添加剂"


def test_extracts_title_from_first_heading_when_missing():
    state = _make_state("# GB 2760-2024 食品添加剂使用标准\n\n## 范围", {"standard_no": "GB2760"})
    result = parse_node(state)
    assert "GB 2760" in result["doc_metadata"]["title"]


def test_does_not_override_provided_title():
    state = _make_state("# 不同标题\n内容", {"standard_no": "GB2760", "title": "提供的标题"})
    result = parse_node(state)
    assert result["doc_metadata"]["title"] == "提供的标题"


def test_missing_standard_no_adds_error():
    state = _make_state("## 范围\n内容", {"title": "某标准"})
    result = parse_node(state)
    assert len(result["errors"]) > 0
    assert "standard_no" in result["errors"][0]


def test_md_content_preserved():
    md = "## 范围\n内容"
    state = _make_state(md, {"standard_no": "GB2760", "title": "t"})
    result = parse_node(state)
    assert result["md_content"] == md

