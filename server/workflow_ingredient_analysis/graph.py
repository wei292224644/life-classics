"""LangGraph compilation for ingredient_analysis workflow."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.retrieve_evidence_node import retrieve_evidence_node
from workflow_ingredient_analysis.nodes.analyze_node import analyze_node
from workflow_ingredient_analysis.nodes.compose_output_node import compose_output_node


def _should_skip_analysis(state: WorkflowState) -> str:
    """如果 evidence_refs 为空，跳过 analyze_node 直接进入 compose_output_node."""
    evidence_refs = state.get("evidence_refs") or []
    if not evidence_refs:
        return "compose_output_node"
    return "analyze_node"


def _build_graph():
    builder = StateGraph(WorkflowState)

    builder.add_node("retrieve_evidence_node", retrieve_evidence_node)
    builder.add_node("analyze_node", analyze_node)
    builder.add_node("compose_output_node", compose_output_node)

    builder.set_entry_point("retrieve_evidence_node")

    # retrieve_evidence → analyze_node（有证据时）或 compose_output_node（无证据时）
    builder.add_conditional_edges(
        "retrieve_evidence_node",
        _should_skip_analysis,
        {
            "analyze_node": "analyze_node",
            "compose_output_node": "compose_output_node",
        },
    )

    # analyze_node → compose_output_node
    builder.add_edge("analyze_node", "compose_output_node")

    # compose_output_node → END
    builder.add_edge("compose_output_node", END)

    return builder.compile()


ingredient_analysis_graph = _build_graph()