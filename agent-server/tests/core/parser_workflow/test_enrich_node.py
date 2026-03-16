from __future__ import annotations

import pytest
from typing import Dict, List
from app.core.parser_workflow.nodes.enrich_node import (
    build_table_label_index,
    extract_table_refs,
    extract_other_refs,
)
from app.core.parser_workflow.models import RawChunk


# ── build_table_label_index ──────────────────────────────────────────


def test_build_index_finds_table_at_start_of_chunk():
    """raw_chunk 以表格标题行开头时应被索引"""
    rc: RawChunk = {
        "content": "表1 样品浓缩条件\n\n| 参数 | 值 |\n|---|---|\n| 温度 | 25℃ |",
        "section_path": ["5", "5.1"],
        "char_count": 50,
    }
    index = build_table_label_index([rc])
    assert "表1" in index
    assert "温度" in index["表1"]


def test_build_index_finds_table_in_middle_of_chunk():
    """表格标题行不在 chunk 开头时也应被索引"""
    rc: RawChunk = {
        "content": "以下为测试参数：\n\n表1 样品浓缩条件\n\n| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        "section_path": ["5"],
        "char_count": 80,
    }
    index = build_table_label_index([rc])
    assert "表1" in index


def test_build_index_handles_table_with_space_in_label():
    """'表 1'（含空格）也应规范化为'表1'后被索引"""
    rc: RawChunk = {
        "content": "表 1 卡拉胶质量指标\n\n| 项目 | 指标 |",
        "section_path": ["3"],
        "char_count": 40,
    }
    index = build_table_label_index([rc])
    assert "表1" in index


def test_build_index_handles_lettered_table():
    """'表A.1'格式的表格标签应被正确索引"""
    rc: RawChunk = {
        "content": "表A.1 添加回收率\n\n| 浓度 | 回收率 |",
        "section_path": ["附录A"],
        "char_count": 40,
    }
    index = build_table_label_index([rc])
    assert "表A.1" in index


def test_build_index_empty_when_no_table_title():
    """无表格标题行的 chunk 不应进入索引"""
    rc: RawChunk = {
        "content": "这是普通正文，没有表格。",
        "section_path": ["1"],
        "char_count": 12,
    }
    index = build_table_label_index([rc])
    assert len(index) == 0


# ── extract_table_refs ───────────────────────────────────────────────


def test_extract_table_refs_basic():
    """'见表1'应提取出标准化标签'表1'"""
    refs = extract_table_refs("样品浓缩条件见表1。")
    assert "表1" in refs


def test_extract_table_refs_with_context_prefix():
    """'条件见表1'类带前缀的引用也应提取"""
    refs = extract_table_refs("a）样品浓缩条件见表1；")
    assert "表1" in refs


def test_extract_table_refs_canjian():
    """'参见表A.1'应提取'表A.1'"""
    refs = extract_table_refs("规格参见表A.1。")
    assert "表A.1" in refs


def test_extract_table_refs_canzhao():
    """'参照表B.1'应提取'表B.1'"""
    refs = extract_table_refs("参照表B.1进行操作。")
    assert "表B.1" in refs


def test_extract_table_refs_returns_empty_for_no_ref():
    """无表格引用时返回空列表"""
    refs = extract_table_refs("本节描述检测方法。")
    assert refs == []


# ── extract_other_refs ───────────────────────────────────────────────


def test_extract_other_refs_figure():
    """'见图A.1'应提取'图A.1'"""
    refs = extract_other_refs("色谱图见图A.1。")
    assert any("图A.1" in r for r in refs)


def test_extract_other_refs_appendix():
    """'见附录A'应提取附录引用"""
    refs = extract_other_refs("具体见附录A。")
    assert any("附录A" in r for r in refs)


def test_extract_other_refs_canzhao():
    """'参照图A.2'应提取图引用"""
    refs = extract_other_refs("参照图A.2所示操作。")
    assert any("图A.2" in r for r in refs)


def test_extract_other_refs_no_table():
    """纯表格引用不应出现在 other_refs 中"""
    refs = extract_other_refs("条件见表1。")
    assert refs == []
from app.core.parser_workflow.nodes.enrich_node import resolve_table_ref
from app.core.parser_workflow.models import ClassifiedChunk, TypedSegment


# ── resolve_table_ref ────────────────────────────────────────────────


def _make_classified_chunk(section_path, content_type="table") -> ClassifiedChunk:
    raw: RawChunk = {
        "content": "| 项目 | 指标 |\n|---|---|\n| 水分 | ≤12% |",
        "section_path": section_path,
        "char_count": 40,
    }
    seg: TypedSegment = {
        "content": "| 项目 | 指标 |",
        "content_type": content_type,
        "transform_params": {"strategy": "split_rows", "prompt_template": ""},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    return ClassifiedChunk(raw_chunk=raw, segments=[seg], has_unknown=False)


def test_resolve_hits_label_index():
    """正则索引命中时直接返回 chunk 内容"""
    index = {"表1": "| 参数 | 值 |\n|---|---|\n| 温度 | 25℃ |"}
    result = resolve_table_ref("表1", index, [])
    assert result is not None
    assert "温度" in result


def test_resolve_falls_back_to_section_path():
    """正则索引未命中时，通过 section_path 模糊匹配找到 table chunk"""
    index: Dict[str, str] = {}
    cc = _make_classified_chunk(["5", "表1 卡拉胶质量指标"])
    result = resolve_table_ref("表1", index, [cc])
    assert result is not None
    assert "水分" in result


def test_resolve_section_path_normalizes_spaces():
    """section_path 含空格的标签也能匹配（规范化后比较）"""
    index: Dict[str, str] = {}
    cc = _make_classified_chunk(["5", "表 1 卡拉胶质量指标"])
    result = resolve_table_ref("表1", index, [cc])
    assert result is not None


def test_resolve_returns_none_when_not_found():
    """两步都未命中时返回 None"""
    index: Dict[str, str] = {}
    cc = _make_classified_chunk(["5", "表2 其他指标"])
    result = resolve_table_ref("表1", index, [cc])
    assert result is None


def test_resolve_ignores_non_table_chunks():
    """content_type 非 table 的 chunk 不参与 section_path 匹配"""
    index: Dict[str, str] = {}
    cc = _make_classified_chunk(["5", "表1 卡拉胶质量指标"], content_type="plain_text")
    result = resolve_table_ref("表1", index, [cc])
    assert result is None


from app.core.parser_workflow.nodes.enrich_node import enrich_node


# ── enrich_node ──────────────────────────────────────────────────────


def _make_state(seg_content: str, raw_chunks=None, extra_classified=None) -> dict:
    """构造最小化的 WorkflowState 用于 enrich_node 测试"""
    table_raw: RawChunk = {
        "content": "表1 样品浓缩条件\n\n| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        "section_path": ["5", "5.1"],
        "char_count": 60,
    }
    ref_raw: RawChunk = {
        "content": seg_content,
        "section_path": ["5", "5.2"],
        "char_count": len(seg_content),
    }
    ref_seg: TypedSegment = {
        "content": seg_content,
        "content_type": "plain_text",
        "transform_params": {"strategy": "semantic_standardization", "prompt_template": ""},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    table_seg: TypedSegment = {
        "content": "| 参数 | 值 |",
        "content_type": "table",
        "transform_params": {"strategy": "split_rows", "prompt_template": ""},
        "confidence": 0.95,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    ref_cc = ClassifiedChunk(raw_chunk=ref_raw, segments=[ref_seg], has_unknown=False)
    table_cc = ClassifiedChunk(raw_chunk=table_raw, segments=[table_seg], has_unknown=False)
    chunks = [ref_cc, table_cc] + (extra_classified or [])
    return {
        "md_content": "",
        "doc_metadata": {"standard_no": "GB-001"},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": (raw_chunks if raw_chunks is not None else [table_raw, ref_raw]),
        "classified_chunks": chunks,
        "final_chunks": [],
        "errors": [],
    }


def test_enrich_node_inlines_table_via_label_index():
    """见表1 引用能通过正则标签索引内联表格内容"""
    state = _make_state("a）样品浓缩条件见表1；")
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert segs[0]["ref_context"] != ""
    assert "流速" in segs[0]["ref_context"]


def test_enrich_node_inlines_table_via_section_path():
    """正则索引未命中时通过 section_path 回退匹配"""
    # 表格 raw_chunk 内容无标题行 → label_index 为空 → 强制走 section_path 路径
    table_raw_no_title: RawChunk = {
        "content": "| 参数 | 值 |\n|---|---|\n| 流速 | 5mL/min |",
        "section_path": ["5", "表1 样品浓缩条件"],
        "char_count": 40,
    }
    table_seg: TypedSegment = {
        "content": "| 参数 | 值 |",
        "content_type": "table",
        "transform_params": {"strategy": "split_rows", "prompt_template": ""},
        "confidence": 0.95,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    ref_raw: RawChunk = {
        "content": "样品浓缩条件见表1",
        "section_path": ["5", "5.2"],
        "char_count": 9,
    }
    ref_seg: TypedSegment = {
        "content": "样品浓缩条件见表1",
        "content_type": "plain_text",
        "transform_params": {"strategy": "semantic_standardization", "prompt_template": ""},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    table_cc = ClassifiedChunk(raw_chunk=table_raw_no_title, segments=[table_seg], has_unknown=False)
    ref_cc = ClassifiedChunk(raw_chunk=ref_raw, segments=[ref_seg], has_unknown=False)
    state = {
        "md_content": "",
        "doc_metadata": {"standard_no": "GB-001"},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": [table_raw_no_title, ref_raw],
        "classified_chunks": [ref_cc, table_cc],
        "final_chunks": [],
        "errors": [],
    }
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert "流速" in segs[0]["ref_context"]


def test_enrich_node_records_cross_refs():
    """识别到的引用（包括图/附录）均应写入 cross_refs"""
    state = _make_state("条件见表1，色谱图见图A.1。")
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert "表1" in segs[0]["cross_refs"]
    assert any("图A.1" in r for r in segs[0]["cross_refs"])


def test_enrich_node_other_refs_not_inlined():
    """图/附录引用只记录 cross_refs，ref_context 仍为空"""
    state = _make_state("具体见附录A，色谱图见图A.1。")
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert segs[0]["ref_context"] == ""
    assert len(segs[0]["cross_refs"]) > 0


def test_enrich_node_unresolved_table_writes_error():
    """表格引用未命中时写入 errors 警告，不抛异常"""
    state = _make_state("条件见表99。")  # 表99 不存在
    result = enrich_node(state)
    assert any("表99" in e for e in result["errors"])


def test_enrich_node_appends_to_existing_errors():
    """enrich_node 追加 errors，不覆盖上游已有的错误"""
    state = _make_state("条件见表99。")
    state["errors"] = ["ERROR: 上游已有错误"]
    result = enrich_node(state)
    assert "ERROR: 上游已有错误" in result["errors"]
    assert any("表99" in e for e in result["errors"])


def test_enrich_node_meta_records_failed_table_refs():
    """未能解析的表格引用写入 TypedSegment.failed_table_refs"""
    state = _make_state("条件见表99。")
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert "表99" in segs[0]["failed_table_refs"]
    assert segs[0]["ref_context"] == ""


def test_enrich_node_partial_resolution_tracks_failed():
    """部分表格引用解析成功、部分失败时，failed_table_refs 只含失败的"""
    state = _make_state("条件见表1，规格见表99。")  # 表1 能解析，表99 不能
    result = enrich_node(state)
    segs = result["classified_chunks"][0]["segments"]
    assert "表99" in segs[0]["failed_table_refs"]
    assert "表1" not in segs[0]["failed_table_refs"]
    assert segs[0]["ref_context"] != ""  # 表1 的内容已内联


def test_enrich_node_sees_table_corrected_by_escalate():
    """escalate_node 将 unknown 段修正为 table 后，enrich_node 应能通过 section_path 匹配该表格"""
    # 模拟 escalate_node 输出：原 unknown 段已被修正为 table
    table_raw: RawChunk = {
        "content": "| 项目 | 指标 |\n|---|---|\n| 水分 | ≤12% |",
        "section_path": ["3", "表1 卡拉胶质量要求"],
        "char_count": 40,
    }
    escalated_seg: TypedSegment = {
        "content": "| 项目 | 指标 |",
        "content_type": "table",      # escalate_node 修正后的类型
        "transform_params": {"strategy": "split_rows", "prompt_template": ""},
        "confidence": 1.0,
        "escalated": True,            # 标记为已 escalate
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    ref_raw: RawChunk = {
        "content": "感官要求见表1。",
        "section_path": ["3", "3.1"],
        "char_count": 8,
    }
    ref_seg: TypedSegment = {
        "content": "感官要求见表1。",
        "content_type": "plain_text",
        "transform_params": {"strategy": "semantic_standardization", "prompt_template": ""},
        "confidence": 0.9,
        "escalated": False,
        "cross_refs": [],
        "ref_context": "",
        "failed_table_refs": [],
    }
    table_cc = ClassifiedChunk(raw_chunk=table_raw, segments=[escalated_seg], has_unknown=False)
    ref_cc = ClassifiedChunk(raw_chunk=ref_raw, segments=[ref_seg], has_unknown=False)
    state = {
        "md_content": "",
        "doc_metadata": {"standard_no": "GB-001"},
        "config": {},
        "rules_dir": "rules",
        "raw_chunks": [table_raw, ref_raw],
        "classified_chunks": [ref_cc, table_cc],
        "final_chunks": [],
        "errors": [],
    }
    result = enrich_node(state)
    ref_segs = result["classified_chunks"][0]["segments"]
    # section_path 包含 "表1"，应能通过回退匹配找到表格内容
    assert "水分" in ref_segs[0]["ref_context"]
