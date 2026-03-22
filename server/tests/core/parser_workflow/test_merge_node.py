from __future__ import annotations

import json

import pytest

from parser.models import DocumentChunk, WorkflowState
from parser.nodes.merge_node import (
    _chunks_from_same_raw,
    _merge_two,
    _same_classification,
    merge_node,
)


# ── _chunks_from_same_raw ───────────────────────────────────────────────────


def test_chunks_from_same_raw_equal():
    a = DocumentChunk(
        chunk_id="a1",
        doc_metadata={},
        section_path=["1"],
        structure_type="paragraph",
        semantic_type="scope",
        content="内容A",
        raw_content="原始内容",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    b = DocumentChunk(
        chunk_id="a2",
        doc_metadata={},
        section_path=["1"],
        structure_type="paragraph",
        semantic_type="scope",
        content="内容B",
        raw_content="原始内容",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    assert _chunks_from_same_raw(a, b) is True


def test_chunks_from_same_raw_different():
    a = DocumentChunk(
        chunk_id="a1",
        doc_metadata={},
        section_path=["1"],
        structure_type="paragraph",
        semantic_type="scope",
        content="内容A",
        raw_content="原始内容A",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    b = DocumentChunk(
        chunk_id="a2",
        doc_metadata={},
        section_path=["1"],
        structure_type="paragraph",
        semantic_type="scope",
        content="内容B",
        raw_content="原始内容B",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    assert _chunks_from_same_raw(a, b) is False


# ── _same_classification ────────────────────────────────────────────────────


def test_same_classification_true():
    a = DocumentChunk(
        chunk_id="a1",
        doc_metadata={},
        section_path=["4", "试剂和材料"],
        structure_type="list",
        semantic_type="material",
        content="内容A",
        raw_content="原始",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    b = DocumentChunk(
        chunk_id="a2",
        doc_metadata={},
        section_path=["4", "试剂和材料"],
        structure_type="list",
        semantic_type="material",
        content="内容B",
        raw_content="原始",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    assert _same_classification(a, b) is True


def test_same_classification_different_section_path():
    a = DocumentChunk(
        chunk_id="a1",
        doc_metadata={},
        section_path=["4", "试剂和材料"],
        structure_type="list",
        semantic_type="material",
        content="内容A",
        raw_content="原始",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    b = DocumentChunk(
        chunk_id="a2",
        doc_metadata={},
        section_path=["5", "仪器和设备"],
        structure_type="list",
        semantic_type="material",
        content="内容B",
        raw_content="原始",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    assert _same_classification(a, b) is False


def test_same_classification_different_semantic_type():
    a = DocumentChunk(
        chunk_id="a1",
        doc_metadata={},
        section_path=["4", "试剂和材料"],
        structure_type="list",
        semantic_type="material",
        content="内容A",
        raw_content="原始",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    b = DocumentChunk(
        chunk_id="a2",
        doc_metadata={},
        section_path=["4", "试剂和材料"],
        structure_type="list",
        semantic_type="procedure",
        content="内容B",
        raw_content="原始",
        meta={"cross_refs": [], "failed_table_refs": []},
    )
    assert _same_classification(a, b) is False


# ── _merge_two ───────────────────────────────────────────────────────────────


def test_merge_two_combines_content():
    a = DocumentChunk(
        chunk_id="a1",
        doc_metadata={"doc_id": "doc1"},
        section_path=["4"],
        structure_type="list",
        semantic_type="material",
        content="4.6 1 mg/mL 甲砜霉素标准贮备液：...",
        raw_content="# 4 试剂和材料\n\n4.6 ...",
        meta={
            "cross_refs": [],
            "non_table_refs": [],
            "failed_table_refs": [],
            "segment_raw_content": "4.6 1 mg/mL...",
        },
    )
    b = DocumentChunk(
        chunk_id="b1",
        doc_metadata={"doc_id": "doc1"},
        section_path=["4"],
        structure_type="list",
        semantic_type="material",
        content="4.7 10 μg/mL 甲砜霉素标准工作液：...",
        raw_content="# 4 试剂和材料\n\n4.7 ...",
        meta={
            "cross_refs": [],
            "non_table_refs": [],
            "failed_table_refs": [],
            "segment_raw_content": "4.7 10 μg/mL...",
        },
    )
    result = _merge_two(a, b)

    assert "\n\n" in result["content"]
    assert a["content"] in result["content"]
    assert b["content"] in result["content"]
    assert "\n\n" in result["raw_content"]
    assert "\n\n" in result["meta"]["segment_raw_content"]
    assert result["section_path"] == a["section_path"]
    assert result["semantic_type"] == a["semantic_type"]


def test_merge_two_merges_cross_refs():
    a = DocumentChunk(
        chunk_id="a1",
        doc_metadata={"doc_id": "doc1"},
        section_path=["7"],
        structure_type="paragraph",
        semantic_type="procedure",
        content="内容A",
        raw_content="原始",
        meta={
            "cross_refs": ["表1"],
            "non_table_refs": [],
            "failed_table_refs": [],
            "segment_raw_content": "",
        },
    )
    b = DocumentChunk(
        chunk_id="b1",
        doc_metadata={"doc_id": "doc1"},
        section_path=["7"],
        structure_type="paragraph",
        semantic_type="procedure",
        content="内容B",
        raw_content="原始",
        meta={
            "cross_refs": ["表1", "附录A"],
            "non_table_refs": ["附录A"],
            "failed_table_refs": [],
            "segment_raw_content": "",
        },
    )
    result = _merge_two(a, b)

    assert set(result["meta"]["cross_refs"]) == {"表1", "附录A"}
    assert set(result["meta"]["failed_table_refs"]) == set()


# ── merge_node ───────────────────────────────────────────────────────────────


def test_merge_node_empty():
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "",
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": [],
        "errors": [],
    }
    result = merge_node(state)
    assert result["final_chunks"] == []


def test_merge_node_no_adjacent_same_raw():
    """没有相邻且 raw_content 相同的 chunk，不合并"""
    chunks: list[DocumentChunk] = [
        {
            "chunk_id": "c1",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["1"],
            "structure_type": "paragraph",
            "semantic_type": "scope",
            "content": "内容1",
            "raw_content": "原始1",
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": ""},
        },
        {
            "chunk_id": "c2",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["2"],
            "structure_type": "paragraph",
            "semantic_type": "scope",
            "content": "内容2",
            "raw_content": "原始2",
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": ""},
        },
    ]
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "",
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": chunks,
        "errors": [],
    }
    result = merge_node(state)
    assert len(result["final_chunks"]) == 2


def test_merge_node_merges_adjacent_same_raw_and_classification():
    """相邻且 raw_content 相同、classification 相同的两个 chunk 应合并"""
    raw = "# 4 试剂和材料\n\n4.6 ..."
    chunks: list[DocumentChunk] = [
        {
            "chunk_id": "c1",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "4.6 1 mg/mL 甲砜霉素标准贮备液：...",
            "raw_content": raw,
            "meta": {
                "cross_refs": [],
                "non_table_refs": [],
                "failed_table_refs": [],
                "segment_raw_content": "4.6 1 mg/mL...",
            },
        },
        {
            "chunk_id": "c2",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "4.7 10 μg/mL 甲砜霉素标准工作液：...",
            "raw_content": raw,
            "meta": {
                "cross_refs": [],
                "non_table_refs": [],
                "failed_table_refs": [],
                "segment_raw_content": "4.7 10 μg/mL...",
            },
        },
    ]
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "",
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": chunks,
        "errors": [],
    }
    result = merge_node(state)
    assert len(result["final_chunks"]) == 1
    assert "4.6" in result["final_chunks"][0]["content"]
    assert "4.7" in result["final_chunks"][0]["content"]


def test_merge_node_does_not_merge_different_raw():
    """raw_content 不同，不合并"""
    chunks: list[DocumentChunk] = [
        {
            "chunk_id": "c1",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "内容1",
            "raw_content": "原始1",
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": ""},
        },
        {
            "chunk_id": "c2",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "内容2",
            "raw_content": "原始2",
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": ""},
        },
    ]
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "",
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": chunks,
        "errors": [],
    }
    result = merge_node(state)
    assert len(result["final_chunks"]) == 2


def test_merge_node_does_not_merge_different_semantic_type():
    """semantic_type 不同，即使 raw_content 相同也不合并"""
    raw = "# 4 试剂和材料\n\n4.6 ..."
    chunks: list[DocumentChunk] = [
        {
            "chunk_id": "c1",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "paragraph",
            "semantic_type": "material",
            "content": "内容1",
            "raw_content": raw,
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": ""},
        },
        {
            "chunk_id": "c2",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "paragraph",
            "semantic_type": "procedure",
            "content": "内容2",
            "raw_content": raw,
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": ""},
        },
    ]
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "",
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": chunks,
        "errors": [],
    }
    result = merge_node(state)
    assert len(result["final_chunks"]) == 2


def test_merge_two_raw_content_not_duplicated():
    """合并同源 chunk 时，raw_content 不应重复拼接（两者相同，取其一即可）"""
    raw = "# 4 试剂和材料\n\n4.6 甲砜霉素标准贮备液：配置方法..."
    a = DocumentChunk(
        chunk_id="a1", doc_metadata={"doc_id": "doc1"}, section_path=["4"],
        structure_type="list", semantic_type="material",
        content="4.6 甲砜霉素标准贮备液：...", raw_content=raw,
        meta={"cross_refs": [], "non_table_refs": [], "failed_table_refs": [],
              "segment_raw_content": "4.6 甲砜霉素标准贮备液：...", "cross_ref_standards": []},
    )
    b = DocumentChunk(
        chunk_id="b1", doc_metadata={"doc_id": "doc1"}, section_path=["4"],
        structure_type="list", semantic_type="material",
        content="4.7 甲砜霉素标准工作液：...", raw_content=raw,
        meta={"cross_refs": [], "non_table_refs": [], "failed_table_refs": [],
              "segment_raw_content": "4.7 甲砜霉素标准工作液：...", "cross_ref_standards": []},
    )
    result = _merge_two(a, b)
    # raw_content 不应被重复拼接
    assert result["raw_content"] == raw
    # content 和 segment_raw_content 应正常拼接
    assert "4.6" in result["content"] and "4.7" in result["content"]
    assert "4.6" in result["meta"]["segment_raw_content"] and "4.7" in result["meta"]["segment_raw_content"]


def test_merge_node_merges_all_same_raw_same_classification():
    """同一 raw_chunk 的所有相邻同分类 segment 应全部合并为 1 个 chunk"""
    raw = "# 4 试剂和材料\n\n..."
    chunks: list[DocumentChunk] = [
        {
            "chunk_id": "c1",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "4.5 C18 柱",
            "raw_content": raw,
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": "4.5"},
        },
        {
            "chunk_id": "c2",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "4.6 标准贮备液",
            "raw_content": raw,
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": "4.6"},
        },
        {
            "chunk_id": "c3",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "4.7 标准工作液",
            "raw_content": raw,
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": "4.7"},
        },
    ]
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "",
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": chunks,
        "errors": [],
    }
    result = merge_node(state)
    # 三个 chunk 来自同一 raw_chunk，全部合并为 1
    assert len(result["final_chunks"]) == 1
    merged = result["final_chunks"][0]
    assert "4.5" in merged["content"]
    assert "4.6" in merged["content"]
    assert "4.7" in merged["content"]


def test_merge_node_stops_at_different_raw_chunk():
    """不同 raw_chunk 来源的 chunk 不合并，即使分类相同"""
    raw_a = "# 4 试剂和材料\n\n4.5-4.6"
    raw_b = "# 4 试剂和材料\n\n4.7"  # 不同的 raw_chunk 内容
    chunks: list[DocumentChunk] = [
        {
            "chunk_id": "c1",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "4.5 C18 柱",
            "raw_content": raw_a,
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": "4.5"},
        },
        {
            "chunk_id": "c2",
            "doc_metadata": {"doc_id": "d1"},
            "section_path": ["4"],
            "structure_type": "list",
            "semantic_type": "material",
            "content": "4.7 标准工作液",
            "raw_content": raw_b,
            "meta": {"cross_refs": [], "non_table_refs": [], "failed_table_refs": [], "segment_raw_content": "4.7"},
        },
    ]
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": {},
        "config": {},
        "rules_dir": "",
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": chunks,
        "errors": [],
    }
    result = merge_node(state)
    # 不同 raw_chunk，不合并
    assert len(result["final_chunks"]) == 2


@pytest.mark.skip(reason="artifact 文件路径已过期，需要重新生成")
def test_merge_node_with_real_artifact():
    """用真实 artifact 数据验证 merge_node 正确合并相邻且满足条件的 chunks"""
    # 加载原始 transform_node 输出（24 chunks）
    with open(
        "/Users/wwj/Desktop/self/life-classics/agent-server/tests/artifacts/parser_workflow_nodes_20260319_151921/08_final_chunks.json"
    ) as f:
        data = json.load(f)
    transform_output: list[dict] = data["node_output"]["final_chunks"]

    # 构造 state
    state: WorkflowState = {
        "md_content": "",
        "doc_metadata": transform_output[0]["doc_metadata"],
        "config": {},
        "rules_dir": "",
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": transform_output,  # type: ignore[arg-type]
        "errors": [],
    }

    result = merge_node(state)
    actual_chunks = result["final_chunks"]

    # 验证合并后 chunk 数量减少（24 → 21，说明发生了 3 次合并）
    assert len(actual_chunks) < len(transform_output), (
        f"Expected fewer chunks than {len(transform_output)}, got {len(actual_chunks)}"
    )
    assert len(actual_chunks) == 21, f"Expected 21 chunks after merge, got {len(actual_chunks)}"

    # 验证 chunks 2+3 合并：2 规范性引用文件的 intro paragraph + 标准列表
    # 合并后 content 应包含 intro 和 GB/T 标准列表
    merged_ref = next(
        (c for c in actual_chunks if "GB/T 1.1-2000" in c["content"]),
        None,
    )
    assert merged_ref is not None, "GB/T 1.1-2000 should be in a merged chunk"
    assert (
        "下列文件中的条款通过本标准的引用而成为本标准的条款" in merged_ref["content"]
    ), "intro text should be in same chunk as GB/T standards"

    # 验证 chunks 5+6 合并：4.1-4.5 + 4.6（来自同一 raw_chunk["content"]）
    merged_46 = next(
        (c for c in actual_chunks if "4.6" in c["content"] and "以下所用的试剂" in c["content"]),
        None,
    )
    assert merged_46 is not None, "4.6 should be merged with 4.1-4.5"

    # 验证 4.7 单独保留（segment_raw_content 不同，未参与合并）
    has_47 = any("4.7" in c["content"] for c in actual_chunks)
    assert has_47, "4.7 should remain as a separate chunk"

    # 验证 chunks 20+21 合并：9 检测方法灵敏度的 9.1 + 9.2
    # 原始 chunks 20+21 都包含 "检测限" 且有相同的 raw/section/sem，合并后只有 1 个包含 "检测限" 的 chunk
    chunks_with_ji_xian = [c for c in actual_chunks if "检测限" in c["content"]]
    assert len(chunks_with_ji_xian) == 1, (
        f"Expected 1 chunk with 检测限 after merging, got {len(chunks_with_ji_xian)}"
    )
