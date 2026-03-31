"""产品分析 Agent 的 4 个 LangGraph 节点。"""
from __future__ import annotations

import asyncio

import structlog

from worflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import (
    ProductAnalysisState,
    DemographicsOutput, ScenariosOutput, AdviceOutput, VerdictOutput,
)
from workflow_product_analysis.types import DemographicItem, ScenarioItem

logger = structlog.get_logger(__name__)


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
        provider=settings.ANALYSIS_LLM_PROVIDER,
        model=settings.ANALYSIS_DEMOGRAPHICS_MODEL,
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
        model=settings.ANALYSIS_DEMOGRAPHICS_MODEL,
        response_model=DemographicsOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    demographics: list[DemographicItem] = [
        {"group": d.group, "level": d.level, "note": d.note}
        for d in result.demographics
    ]
    return {"demographics": demographics}


async def scenarios_node(state: ProductAnalysisState, settings) -> dict:
    """
    Node B：食用场景分析。
    输入：state["ingredients"]
    输出：{"scenarios": list[ScenarioItem]}（1-3 条）
    """
    create = get_structured_client(
        provider=settings.ANALYSIS_LLM_PROVIDER,
        model=settings.ANALYSIS_SCENARIOS_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    prompt = f"""根据以下食品成分，给出 1-3 个具体的食用场景建议：

成分列表：
{summary}

每个场景需包含：title（如"上午加餐"）和 text（具体建议 2-3 句，包含时间段、人群、搭配）。"""

    result: ScenariosOutput = await asyncio.to_thread(
        create,
        model=settings.ANALYSIS_SCENARIOS_MODEL,
        response_model=ScenariosOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    scenarios: list[ScenarioItem] = [
        {"title": s.title, "text": s.text}
        for s in result.scenarios
    ]
    return {"scenarios": scenarios}


async def advice_node(state: ProductAnalysisState, settings) -> dict:
    """
    Node C：综合建议。
    输入：state["ingredients"] + state["demographics"] + state["scenarios"]
    输出：{"advice": str}（1-3 句）
    """
    create = get_structured_client(
        provider=settings.ANALYSIS_LLM_PROVIDER,
        model=settings.ANALYSIS_ADVICE_MODEL,
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
        model=settings.ANALYSIS_ADVICE_MODEL,
        response_model=AdviceOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"advice": result.advice}


async def verdict_node(state: ProductAnalysisState, settings) -> dict:
    """
    Node D：整体判断。
    输入：全部前序产物
    输出：{"verdict_level": RiskLevel, "verdict_description": str, "references": list[str]}

    后处理：对 references 做白名单过滤，仅保留 settings.ANALYSIS_REFERENCES_ALLOWLIST 中的标准。
    """
    create = get_structured_client(
        provider=settings.ANALYSIS_LLM_PROVIDER,
        model=settings.ANALYSIS_VERDICT_MODEL,
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
        model=settings.ANALYSIS_VERDICT_MODEL,
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
