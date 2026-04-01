"""Node C：综合建议。"""
from __future__ import annotations

import asyncio

from workflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import (
    ProductAnalysisState,
    AdviceOutput,
)
from config import settings


def _build_ingredients_summary(ingredients) -> str:
    """将 IngredientInput 列表转为 prompt 用的文字摘要。"""
    lines = []
    for ing in ingredients:
        lines.append(
            f"- {ing['name']} (风险等级: {ing['level']}, 类别: {ing['category']}): {ing['safety_info']}"
        )
    return "\n".join(lines) if lines else "（无成分信息）"


async def advice_node(state: ProductAnalysisState) -> dict:
    """
    Node C：综合建议。
    输入：state["ingredients"] + state["demographics"] + state["scenarios"]
    输出：{"advice": str}（1-3 句）
    """
    create = get_structured_client(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    demo_text = "\n".join(
        [f"- {d['group']}: {d['note']}" for d in (state["demographics"] or [])]
    )
    scene_text = "\n".join(
        [f"- {s['title']}: {s['text']}" for s in (state["scenarios"] or [])]
    )

    prompt = f"""综合以下信息，给出面向普通用户的简短建议（1-3 句，语气实用中立，不做绝对化判断）：

成分：
{summary}

各人群评估：
{demo_text}

食用场景：
{scene_text}"""

    result: AdviceOutput = await asyncio.to_thread(
        create,
        model=settings.DEFAULT_MODEL,
        response_model=AdviceOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"advice": result.advice}