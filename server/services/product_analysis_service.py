"""Product Analysis 业务编排服务 — L2 层，调用 workflow_product_analysis."""
from __future__ import annotations

from workflow_product_analysis.product_agent.graph import (
    ProductAgentError,
    build_product_analysis_graph,
)
from workflow_product_analysis.product_agent.types import ProductAnalysisState
from workflow_product_analysis.types import IngredientInput


class ProductAnalysisService:
    """L2: 产品分析业务编排 — 调用 workflow_product_analysis."""

    def build_graph(self):
        """返回编译后的 LangGraph."""
        return build_product_analysis_graph()

    async def run_product_analysis(
        self,
        ingredients: list[IngredientInput],
    ) -> ProductAnalysisState:
        """
        运行产品分析 workflow.

        Args:
            ingredients: 成分输入列表

        Returns:
            ProductAnalysisState: workflow 执行后的完整状态
        """
        graph = build_product_analysis_graph()
        initial_state: ProductAnalysisState = {
            "ingredients": ingredients,
            "demographics": None,
            "scenarios": None,
            "advice": None,
            "verdict_level": None,
            "verdict_description": None,
            "references": None,
        }
        result = await graph.ainvoke(initial_state)
        return result
