"""Tests for LangGraph product analysis graph."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_product_analysis.product_agent.graph import (
    ProductAgentError,
    build_product_analysis_graph,
    run_product_analysis_agent,
)
from workflow_product_analysis.types import IngredientInput


@pytest.fixture
def mock_settings():
    return MagicMock()


def test_build_graph_returns_compiled(mock_settings):
    """build_product_analysis_graph returns a compiled StateGraph."""
    graph = build_product_analysis_graph(mock_settings)
    assert graph is not None
    # Compiled graph has an invoke method
    assert hasattr(graph, "invoke")


@pytest.mark.asyncio
async def test_run_agent_returns_all_fields(mock_settings):
    """run_product_analysis_agent returns all expected fields."""
    ingredients: list[IngredientInput] = [
        {
            "ingredient_id": 1,
            "name": "糖",
            "category": "甜味剂",
            "level": "t2",
            "safety_info": "",
        }
    ]

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

        result = await run_product_analysis_agent(ingredients, mock_settings)

        assert "demographics" in result
        assert "scenarios" in result
        assert "advice" in result
        assert result["advice"] == "test advice"
        assert result["verdict_level"] == "t1"
        assert result["verdict_description"] == "test product"
        assert result["references"] == []


@pytest.mark.asyncio
async def test_node_exception_raises_product_agent_error(mock_settings):
    """If any node raises, ProductAgentError is raised."""
    ingredients: list[IngredientInput] = []

    with patch(
        "workflow_product_analysis.product_agent.graph.demographics_node",
        new_callable=AsyncMock,
    ) as mock_d:
        mock_d.side_effect = RuntimeError("LLM network error")

        with pytest.raises(ProductAgentError):
            await run_product_analysis_agent(ingredients, mock_settings)
