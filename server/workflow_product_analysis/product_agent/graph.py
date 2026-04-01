"""LangGraph compilation for product analysis agent."""
from __future__ import annotations

from workflow_product_analysis.product_agent.nodes import (
    advice_node,
    demographics_node,
    scenarios_node,
    verdict_node,
)
from workflow_product_analysis.product_agent.types import ProductAnalysisState

# LangGraph imports
from langgraph.graph import END, StateGraph, START


class ProductAgentError(Exception):
    """Raised when any agent node fails."""


def build_product_analysis_graph() -> StateGraph:
    """
    Build the product analysis DAG:

        START
         ├──→ demographics_node ──┐
         │                        ├──→ advice_node → verdict_node → END
         └──→ scenarios_node ────┘

    Both A (demographics) and B (scenarios) run in parallel from START.
    advice_node waits for both to complete before running.
    """
    graph = StateGraph(ProductAnalysisState)

    graph.add_node("demographics_node", demographics_node)
    graph.add_node("scenarios_node", scenarios_node)
    graph.add_node("advice_node", advice_node)
    graph.add_node("verdict_node", verdict_node)

    # Parallel start: A and B both receive the initial state
    graph.add_edge(START, "demographics_node")
    graph.add_edge(START, "scenarios_node")

    # Both A and B feed into advice_node
    graph.add_edge("demographics_node", "advice_node")
    graph.add_edge("scenarios_node", "advice_node")

    # Sequential: advice → verdict → END
    graph.add_edge("advice_node", "verdict_node")
    graph.add_edge("verdict_node", END)

    return graph.compile()
