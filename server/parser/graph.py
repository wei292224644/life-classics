from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any
import uuid

from langgraph.graph import END, StateGraph  # type: ignore[import]
from opentelemetry import trace

from observability.metrics import parser_workflow_duration_seconds
from parser.models import ParserResult, WorkflowState
from parser.nodes.classify_node import classify_node
from parser.nodes.clean_node import clean_node
from parser.nodes.enrich_node import enrich_node
from parser.nodes.escalate_node import escalate_node
from parser.nodes.merge_node import merge_node
from parser.nodes.parse_node import parse_node
from parser.nodes.slice_node import slice_node
from parser.nodes.structure_node import structure_node
from parser.nodes.transform_node import transform_node

_tracer = trace.get_tracer(__name__)


def _should_escalate(state: WorkflowState) -> str:
    if any(c["has_unknown"] for c in state["classified_chunks"]):
        return "escalate_node"
    return "enrich_node"


def _build_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("parse_node", parse_node)
    builder.add_node("clean_node", clean_node)
    builder.add_node("structure_node", structure_node)
    builder.add_node("slice_node", slice_node)
    builder.add_node("classify_node", classify_node)
    builder.add_node("escalate_node", escalate_node)
    builder.add_node("enrich_node", enrich_node)
    builder.add_node("transform_node", transform_node)
    builder.add_node("merge_node", merge_node)

    builder.set_entry_point("parse_node")
    builder.add_edge("parse_node", "clean_node")
    builder.add_edge("clean_node", "structure_node")
    builder.add_edge("structure_node", "slice_node")
    builder.add_edge("slice_node", "classify_node")
    builder.add_conditional_edges("classify_node", _should_escalate)
    builder.add_edge("escalate_node", "enrich_node")
    builder.add_edge("enrich_node", "transform_node")
    builder.add_edge("transform_node", "merge_node")
    builder.add_edge("merge_node", END)
    return builder.compile()


parser_graph = _build_graph()


async def run_parser_workflow(
    md_content: str,
    doc_metadata: dict,
    rules_dir: str,
    config: dict | None = None,
) -> ParserResult:
    start_time = time.perf_counter()
    with _tracer.start_as_current_span("parser_workflow") as root_span:
        root_span.set_attribute("parser.doc_id", doc_metadata.get("doc_id", ""))
        initial_state = WorkflowState(
            md_content=md_content,
            doc_metadata=doc_metadata,
            config=config or {},
            rules_dir=rules_dir,
            raw_chunks=[],
            classified_chunks=[],
            final_chunks=[],
            errors=[],
        )
        result_state = await parser_graph.ainvoke(initial_state)
        doc_type = result_state.get("doc_metadata", {}).get("doc_type", "unknown")
        root_span.set_attribute("parser.doc_type", doc_type)
    duration = time.perf_counter() - start_time
    parser_workflow_duration_seconds.labels(doc_type=doc_type).observe(duration)
    escalate_count = sum(
        1
        for c in result_state["classified_chunks"]
        if any(s.get("escalated") for s in c["segments"])
    )
    return ParserResult(
        chunks=result_state["final_chunks"],
        doc_metadata=result_state["doc_metadata"],
        errors=result_state["errors"],
        stats={
            "chunk_count": len(result_state["final_chunks"]),
            "escalate_count": escalate_count,
        },
    )


# 节点名集合，对应前端 PIPELINE_STAGES 的 id（去掉 _node 后缀）
_PIPELINE_NODE_NAMES = {
    "parse_node",
    "clean_node",
    "structure_node",
    "slice_node",
    "classify_node",
    "escalate_node",
    "enrich_node",
    "transform_node",
    "merge_node",
}


async def run_parser_workflow_stream(
    md_content: str,
    doc_name: str,
    rules_dir: str,
    config: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """流式执行 parser workflow，每个节点开始/结束时 yield 进度事件。

    使用 metadata["langgraph_node"] 过滤节点边界事件（比 event["name"] 更可靠，
    可排除 LLM 调用、RunnableSequence 等子事件的干扰）。

    Yields:
        {"type": "stage", "stage": str, "status": "active" | "done"}
        {"type": "workflow_done", "chunks": list[DocumentChunk]}
    """
    start_time = time.perf_counter()
    doc_id = str(uuid.uuid4())
    doc_type = "standard"
    initial_state = WorkflowState(
        md_content=md_content,
        doc_metadata={
            "doc_id": doc_id,
            "title": doc_name,
            "doc_type": doc_type,
        },
        config=config or {},
        rules_dir=rules_dir,
        raw_chunks=[],
        classified_chunks=[],
        final_chunks=[],
        errors=[],
    )
    try:
        with _tracer.start_as_current_span("parser_workflow_stream") as root_span:
            root_span.set_attribute("parser.doc_id", doc_id)
            async for event in parser_graph.astream_events(initial_state, version="v2"):
                event_type = event.get("event", "")
                # 用 metadata.langgraph_node 定位节点边界（比 event["name"] 更可靠）
                node_name = event.get("metadata", {}).get("langgraph_node", "")

                if node_name not in _PIPELINE_NODE_NAMES:
                    continue

                stage = node_name.removesuffix("_node")

                if event_type == "on_chain_start":
                    yield {"type": "stage", "stage": stage, "status": "active"}

                elif event_type == "on_chain_end":
                    # 在 "workflow_done" 事件中捕获最终 doc_type
                    if node_name == "merge_node":
                        output = event.get("data", {}).get("output") or {}
                        result_doc_metadata = output.get("doc_metadata") or {}
                        print(f"result_doc_metadata: {result_doc_metadata}")
                        # 确保 doc_id 始终存在（防止 merge_node 输出未包含该字段）
                        if not result_doc_metadata.get("doc_id"):
                            result_doc_metadata = {**result_doc_metadata, "doc_id": doc_id}
                        doc_type = result_doc_metadata.get("doc_type", "unknown")
                        root_span.set_attribute("parser.doc_type", doc_type)
                        final_chunks = output.get("final_chunks", [])
                        yield {
                            "type": "workflow_done",
                            "chunks": final_chunks,
                            "doc_metadata": result_doc_metadata,
                        }
                    yield {"type": "stage", "stage": stage, "status": "done"}
    finally:
        parser_workflow_duration_seconds.labels(doc_type=doc_type or "unknown").observe(
            time.perf_counter() - start_time
        )
