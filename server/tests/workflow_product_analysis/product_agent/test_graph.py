"""Tests for LangGraph product analysis graph."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from workflow_product_analysis.product_agent.graph import (
    ProductAgentError,
    build_product_analysis_graph,
)
from workflow_product_analysis.product_agent.types import ProductAnalysisState


def test_build_graph_returns_compiled():
    """build_product_analysis_graph returns a compiled StateGraph."""
    graph = build_product_analysis_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


@pytest.mark.asyncio
async def test_invoke_returns_all_fields():
    """graph.ainvoke returns all expected fields from final_state."""
    ingredients = [
        {
            "ingredient_id": 1,
            "name": "糖",
            "category": "甜味剂",
            "level": "t2",
            "safety_info": "",
        }
    ]
    initial_state = ProductAnalysisState(
        ingredients=ingredients,
        demographics=None,
        scenarios=None,
        advice=None,
        verdict_level=None,
        verdict_description=None,
        references=None,
    )

    with patch(
        "workflow_product_analysis.product_agent.graph.demographics_node",
        new_callable=AsyncMock,
    ) as mock_d, patch(
        "workflow_product_analysis.product_agent.graph.scenarios_node",
        new_callable=AsyncMock,
    ) as mock_s, patch(
        "workflow_product_analysis.product_agent.graph.advice_node",
        new_callable=AsyncMock,
    ) as mock_a, patch(
        "workflow_product_analysis.product_agent.graph.verdict_node",
        new_callable=AsyncMock,
    ) as mock_v:

        mock_d.return_value = {"demographics": []}
        mock_s.return_value = {"scenarios": []}
        mock_a.return_value = {"advice": "test advice"}
        mock_v.return_value = {
            "verdict_level": "t1",
            "verdict_description": "test product",
            "references": [],
        }

        graph = build_product_analysis_graph()
        result = await graph.ainvoke(initial_state)

        assert "demographics" in result
        assert "scenarios" in result
        assert "advice" in result
        assert result["advice"] == "test advice"
        assert result["verdict_level"] == "t1"
        assert result["verdict_description"] == "test product"
        assert result["references"] == []
