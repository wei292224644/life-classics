from __future__ import annotations

import time
from typing import List

import structlog
from opentelemetry import trace

from observability.metrics import (
    parser_chunks_processed_total,
    parser_node_duration_seconds,
)
from worflow_parser_kb.models import (
    DocumentChunk,
    WorkflowState,
    make_chunk_id,
)

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


def _chunks_from_same_raw(a: DocumentChunk, b: DocumentChunk) -> bool:
    """比较两个 chunk 的 raw_content 是否相同"""
    return a["raw_content"] == b["raw_content"]


def _same_classification(a: DocumentChunk, b: DocumentChunk) -> bool:
    """比较两个 chunk 的 section_path 和 semantic_type 是否相同"""
    return a["section_path"] == b["section_path"] and a["semantic_type"] == b["semantic_type"]


def _merge_two(a: DocumentChunk, b: DocumentChunk) -> DocumentChunk:
    """将两个 chunk 合并为一个"""
    # content / meta.segment_raw_content — \n\n 拼接
    merged_content = f"{a['content']}\n\n{b['content']}"
    # raw_content 来自同一 raw_chunk（相同），直接取第一个，避免重复拼接
    merged_raw_content = a["raw_content"]
    merged_segment_raw_content = f"{a['meta'].get('segment_raw_content', '')}\n\n{b['meta'].get('segment_raw_content', '')}"

    # meta.cross_refs / meta.failed_table_refs — 取并集
    merged_cross_refs = list(set(a["meta"].get("cross_refs", [])) | set(b["meta"].get("cross_refs", [])))
    merged_failed_table_refs = list(
        set(a["meta"].get("failed_table_refs", [])) | set(b["meta"].get("failed_table_refs", []))
    )

    # chunk_id — 重新生成（基于合并后 content）
    doc_id = a["doc_metadata"].get("doc_id", "")
    merged_chunk_id = make_chunk_id(doc_id, a["section_path"], merged_content)

    # section_path / semantic_type / structure_type / doc_metadata — 取第一个 chunk 的值
    return DocumentChunk(
        chunk_id=merged_chunk_id,
        doc_metadata=a["doc_metadata"],
        section_path=a["section_path"],
        structure_type=a["structure_type"],
        semantic_type=a["semantic_type"],
        content=merged_content,
        raw_content=merged_raw_content,
        meta={
            **a["meta"],
            "segment_raw_content": merged_segment_raw_content,
            "cross_refs": merged_cross_refs,
            "non_table_refs": [r for r in merged_cross_refs if not r.startswith("表")],
            "failed_table_refs": merged_failed_table_refs,
        },
    )


def merge_node(state: WorkflowState) -> dict:
    """遍历 state["final_chunks"]，贪心合并相邻且满足条件的 chunk"""
    _start = time.perf_counter()
    doc_id = state.get("doc_metadata", {}).get("doc_id", "")
    chunks_in = len(state["final_chunks"])
    _logger.info("merge_node_start", node="merge_node", doc_id=doc_id, chunks_in=chunks_in)

    with _tracer.start_as_current_span("merge_node") as span:
        span.set_attribute("worflow_parser_kb.node", "merge_node")
        span.set_attribute("worflow_parser_kb.doc_id", doc_id)
        span.set_attribute("worflow_parser_kb.chunk_count.in", chunks_in)

        chunks = state["final_chunks"]
        if not chunks:
            chunks_out = 0
            span.set_attribute("worflow_parser_kb.chunk_count.out", chunks_out)
            return {"final_chunks": [], "doc_metadata": state.get("doc_metadata", {})}

        merged: List[DocumentChunk] = []
        i = 0
        while i < len(chunks):
            # 从当前 chunk 开始，一直向后合并直到不能合并为止
            merged_chunk = chunks[i]
            j = i + 1
            while j < len(chunks) and _chunks_from_same_raw(merged_chunk, chunks[j]) and _same_classification(
                merged_chunk, chunks[j]
            ):
                merged_chunk = _merge_two(merged_chunk, chunks[j])
                j += 1
            merged.append(merged_chunk)
            i = j

        chunks_out = len(merged)
        span.set_attribute("worflow_parser_kb.chunk_count.out", chunks_out)

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="merge_node").observe(duration)
    parser_chunks_processed_total.labels(node="merge_node").inc(chunks_in)
    _logger.info(
        "merge_node_done",
        node="merge_node",
        doc_id=doc_id,
        duration_ms=round(duration * 1000, 2),
        chunks_in=chunks_in,
        chunks_out=chunks_out,
    )
    return {"final_chunks": merged, "doc_metadata": state.get("doc_metadata", {})}
