import pytest

from app.core.parser_workflow.models import WorkflowState
from app.core.parser_workflow.nodes.slice_node import recursive_slice, slice_node


def _make_state(md: str, config: dict | None = None) -> WorkflowState:
    return WorkflowState(
        md_content=md,
        doc_metadata={"standard_no": "GB_TEST", "title": "测试标准"},
        config=config or {},
        rules_dir="/tmp",
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )


def test_preamble_content_before_first_heading():
    md = "这是前言内容。\n\n## 范围\n\n本标准适用范围。"
    result = slice_node(_make_state(md))
    paths = [c["section_path"] for c in result["raw_chunks"]]
    assert ["__preamble__"] in paths


def test_preamble_not_created_when_no_leading_content():
    md = "## 范围\n\n本标准适用范围。"
    result = slice_node(_make_state(md))
    paths = [c["section_path"] for c in result["raw_chunks"]]
    assert ["__preamble__"] not in paths


def test_splits_on_level2_headings():
    md = "## 范围\n\n内容A。\n\n## 定义\n\n内容B。"
    result = slice_node(_make_state(md))
    section_titles = [c["section_path"][-1] for c in result["raw_chunks"]]
    assert "范围" in section_titles
    assert "定义" in section_titles


def test_recursive_split_when_exceeds_soft_max():
    big_content = "x" * 100
    md = f"## 大章节\n\n### 子节A\n\n{big_content}\n\n### 子节B\n\n{big_content}"
    config = {"chunk_soft_max": 50, "chunk_hard_max": 500}
    result = slice_node(_make_state(md, config))
    section_titles = [c["section_path"][-1] for c in result["raw_chunks"]]
    assert "子节A" in section_titles
    assert "子节B" in section_titles


def test_keeps_chunk_when_no_more_headings_even_if_exceeds_hard_max():
    big_content = "x" * 200
    md = f"## 大章节\n\n{big_content}"
    config = {"chunk_soft_max": 50, "chunk_hard_max": 100}
    result = slice_node(_make_state(md, config))
    assert len(result["raw_chunks"]) >= 1
    assert any("WARN" in e for e in result["errors"])


def test_chunk_char_count_matches_content():
    md = "## 范围\n\n内容。"
    result = slice_node(_make_state(md))
    for chunk in result["raw_chunks"]:
        assert chunk["char_count"] == len(chunk["content"])


def test_no_headings_produces_single_chunk():
    md = "这是一段没有标题的内容。" * 5
    result = slice_node(_make_state(md))
    assert len(result["raw_chunks"]) == 1


def test_section_path_reflects_heading_hierarchy():
    md = "## 检验方法\n\n### 试剂\n\n硫酸。\n\n### 仪器\n\n分光光度计。"
    config = {"chunk_soft_max": 20}
    result = slice_node(_make_state(md, config))
    paths = [c["section_path"] for c in result["raw_chunks"]]
    assert any(len(p) >= 2 and "检验方法" in p[0] and "试剂" in p[-1] for p in paths)
    assert any(len(p) >= 2 and "检验方法" in p[0] and "仪器" in p[-1] for p in paths)


def test_chunk_content_includes_heading_line():
    md = "## 技术要求\n\n理化指标见下表。"
    result = slice_node(_make_state(md))
    chunks = [c for c in result["raw_chunks"] if "技术要求" in c["section_path"][-1]]
    assert len(chunks) == 1
    assert "技术要求" in chunks[0]["content"]

