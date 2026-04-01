"""Node A：人群适用性分析。"""
from __future__ import annotations

import asyncio

from worflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import (
    ProductAnalysisState,
    DemographicsOutput,
)
from workflow_product_analysis.types import DemographicItem


def _build_ingredients_summary(ingredients) -> str:
    """将 IngredientInput 列表转为 prompt 用的文字摘要。"""
    lines = []
    for ing in ingredients:
        lines.append(
            f"- {ing['name']} (风险等级: {ing['level']}, 类别: {ing['category']}): {ing['safety_info']}"
        )
    return "\n".join(lines) if lines else "（无成分信息）"


async def demographics_node(state: ProductAnalysisState, settings) -> dict:
    """
    Node A：人群适用性分析。
    输入：state["ingredients"]
    输出：{"demographics": list[DemographicItem]}（固定 5 条，顺序固定）
    """
    create = get_structured_client(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    prompt = f"""分析以下食品成分对不同人群的适用性：

成分列表：
{summary}

请对以下 5 类人群各输出一条评估（level 为该人群面临的风险等级，note 为 1-2 句具体说明）：
- 普通成人
- 婴幼儿
- 孕妇
- 中老年
- 运动人群"""

    result: DemographicsOutput = await asyncio.to_thread(
        create,
        model=settings.DEFAULT_MODEL,
        response_model=DemographicsOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    demographics: list[DemographicItem] = [
        {"group": d.group, "level": d.level, "note": d.note}
        for d in result.demographics
    ]
    return {"demographics": demographics}