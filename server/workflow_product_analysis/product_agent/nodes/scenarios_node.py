"""Node B：食用场景分析。"""
from __future__ import annotations

import asyncio

from workflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import (
    ProductAnalysisState,
    ScenariosOutput,
)
from workflow_product_analysis.types import ScenarioItem
from config import settings


def _build_ingredients_summary(ingredients) -> str:
    """将 IngredientInput 列表转为 prompt 用的文字摘要。"""
    lines = []
    for ing in ingredients:
        lines.append(
            f"- {ing['name']} (风险等级: {ing['level']}, 类别: {ing['category']}): {ing['safety_info']}"
        )
    return "\n".join(lines) if lines else "（无成分信息）"


async def scenarios_node(state: ProductAnalysisState) -> dict:
    """
    Node B：食用场景分析。
    输入：state["ingredients"]
    输出：{"scenarios": list[ScenarioItem]}（1-3 条）
    """
    create = get_structured_client(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    prompt = f"""根据以下食品成分，给出 1-3 个具体的食用场景建议：

成分列表：
{summary}

每个场景需包含：title（如"上午加餐"）和 text（具体建议 2-3 句，包含时间段、人群、搭配）。"""

    result: ScenariosOutput = await asyncio.to_thread(
        create,
        model=settings.DEFAULT_MODEL,
        response_model=ScenariosOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    scenarios: list[ScenarioItem] = [
        {"title": s.title, "text": s.text}
        for s in result.scenarios
    ]
    return {"scenarios": scenarios}