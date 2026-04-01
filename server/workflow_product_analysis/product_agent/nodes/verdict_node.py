"""Node D：整体判断。"""
from __future__ import annotations

import asyncio
import logging

from workflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import (
    ProductAnalysisState,
    VerdictOutput,
)
from config import settings

logger = logging.getLogger(__name__)


def _build_ingredients_summary(ingredients) -> str:
    """将 IngredientInput 列表转为 prompt 用的文字摘要。"""
    lines = []
    for ing in ingredients:
        lines.append(
            f"- {ing['name']} (风险等级: {ing['level']}, 类别: {ing['category']}): {ing['safety_info']}"
        )
    return "\n".join(lines) if lines else "（无成分信息）"


async def verdict_node(state: ProductAnalysisState) -> dict:
    """
    Node D：整体判断。
    输入：全部前序产物
    输出：{"verdict_level": RiskLevel, "verdict_description": str, "references": list[str]}

    后处理：对 references 做白名单过滤，仅保留 settings.ANALYSIS_REFERENCES_ALLOWLIST 中的标准。
    """
    create = get_structured_client(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    prompt = f"""综合所有分析，给出对该产品的最终整体评估：

成分：
{summary}

各人群评估：
{[d['note'] for d in (state['demographics'] or [])]}

食用建议：{state.get('advice', '')}

请输出：
- level：整体风险等级（t0-t4）
- description：对该产品的特有一句话描述（不能是通用模板）
- references：引用的食品安全标准（如 "GB 2760"，仅引用真实存在的标准）"""

    result: VerdictOutput = await asyncio.to_thread(
        create,
        model=settings.DEFAULT_MODEL,
        response_model=VerdictOutput,
        messages=[{"role": "user", "content": prompt}],
    )

    # ── references 白名单过滤 ─────────────────────────────────────────────
    allowlist_raw = settings.ANALYSIS_REFERENCES_ALLOWLIST.split(",")
    allowlist = {
        s.strip().upper().replace("\u3000", " ").replace("　", " ")
        for s in allowlist_raw
    }

    filtered_refs: list[str] = []
    for ref in result.references:
        normalized = ref.strip().upper().replace("\u3000", " ").replace("　", " ")
        # 宽松匹配：允许带版本号，如 "GB 2760-2014"
        matched = any(normalized.startswith(allowed) for allowed in allowlist)
        if matched:
            filtered_refs.append(ref)
        else:
            logger.warning("reference '%s' not in allowlist, discarded", ref)

    return {
        "verdict_level": result.level,
        "verdict_description": result.description,
        "references": filtered_refs,
    }