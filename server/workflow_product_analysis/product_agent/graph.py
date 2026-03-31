"""LangGraph compilation for product analysis agent."""
from __future__ import annotations

from workflow_product_analysis.product_agent.nodes import (
    advice_node,
    demographics_node,
    scenarios_node,
    verdict_node,
)
from workflow_product_analysis.product_agent.types import ProductAnalysisState
from workflow_product_analysis.types import IngredientInput

# LangGraph imports
from langgraph.graph import END, StateGraph, START


class ProductAgentError(Exception):
    """Raised when any agent node fails."""


def build_product_analysis_graph(settings) -> StateGraph:
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


async def run_product_analysis_agent(
    ingredients: list[IngredientInput],
    settings,
) -> dict:
    """
    Invoke the product analysis agent.

    Args:
        ingredients: List of IngredientInput from the pipeline
        settings: Application settings (contains LLM model configs)

    Returns:
        dict with keys: demographics, scenarios, advice,
                        verdict_level, verdict_description, references

    Raises:
        ProductAgentError: if any node raises an exception
    """
    graph = build_product_analysis_graph(settings)

    initial_state = ProductAnalysisState(
        ingredients=ingredients,
        demographics=None,
        scenarios=None,
        advice=None,
        verdict_level=None,
        verdict_description=None,
        references=None,
    )

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:  # noqa: BLE001
        raise ProductAgentError(f"Agent failed: {exc}") from exc

    return {
        "demographics": final_state.get("demographics"),
        "scenarios": final_state.get("scenarios"),
        "advice": final_state.get("advice"),
        "verdict_level": final_state.get("verdict_level"),
        "verdict_description": final_state.get("verdict_description"),
        "references": final_state.get("references"),
    }
