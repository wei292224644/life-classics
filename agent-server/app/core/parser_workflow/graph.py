from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph  # type: ignore[import]

from app.core.parser_workflow.models import ParserResult, WorkflowState
from app.core.parser_workflow.nodes.classify_node import classify_node
from app.core.parser_workflow.nodes.escalate_node import escalate_node
from app.core.parser_workflow.nodes.parse_node import parse_node
from app.core.parser_workflow.nodes.slice_node import slice_node
from app.core.parser_workflow.nodes.structure_node import structure_node
from app.core.parser_workflow.nodes.transform_node import transform_node


def _should_escalate(state: WorkflowState) -> str:
    if any(c["has_unknown"] for c in state["classified_chunks"]):
        return "escalate_node"
    return "transform_node"


def _build_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("parse_node", parse_node)
    builder.add_node("structure_node", structure_node)
    builder.add_node("slice_node", slice_node)
    builder.add_node("classify_node", classify_node)
    builder.add_node("escalate_node", escalate_node)
    builder.add_node("transform_node", transform_node)

    builder.set_entry_point("parse_node")
    builder.add_edge("parse_node", "structure_node")
    builder.add_edge("structure_node", "slice_node")
    builder.add_edge("slice_node", "classify_node")
    builder.add_conditional_edges("classify_node", _should_escalate)
    builder.add_edge("escalate_node", "transform_node")
    builder.add_edge("transform_node", END)
    return builder.compile()


parser_graph = _build_graph()


async def run_parser_workflow(
    md_content: str,
    doc_metadata: dict,
    rules_dir: str,
    config: dict | None = None,
) -> ParserResult:
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

