"""结果组装器 — 将各阶段产物组装为 ProductAnalysisResult（纯数据组装，无 DB 访问）。"""
from __future__ import annotations

from typing import Any

from database.models import ProductAnalysis
from workflow_product_analysis.types import (
    AlternativeItem,
    IngredientItem,
    ProductAnalysisResult,
)


async def assemble_from_db_cache(
    product_analysis: ProductAnalysis,
    matched_ids: list[int],
    ingredients_data: list[dict],
    analyses_data: dict[int, object],
) -> ProductAnalysisResult:
    """
    从 DB 缓存组装 ProductAnalysisResult。

    source = "db_cache"
    - ingredients[]: 从 matched_ids 组装
    - alternatives[]: 从 matched 成分的 IngredientAnalysis.alternatives 组装
    - verdict: {level, description} ← ProductAnalysis
    - advice ← ProductAnalysis
    - demographics ← ProductAnalysis.demographics（JSONB）
    - scenarios ← ProductAnalysis.scenarios（JSONB）
    - references ← ProductAnalysis.references（ARRAY）
    """
    # 构建 ingredient_map（按 id 索引）
    ingredient_map: dict[int, dict] = {d["id"]: d for d in ingredients_data}

    ingredients: list[IngredientItem] = []
    for ing_id in matched_ids:
        d = ingredient_map.get(ing_id)
        if d is None:
            continue
        analysis = analyses_data.get(ing_id)
        level = analysis.level if analysis else "unknown"
        function_types: list[str] = d.get("function_type") or []
        category = " · ".join(function_types)
        ingredients.append(
            IngredientItem(
                ingredient_id=ing_id,
                name=d["name"],
                category=category,
                level=level,
            )
        )

    # 构建 alternatives（仅 level ∈ {t2, t3, t4}）
    alternatives: list[AlternativeItem] = []
    for ing_id in matched_ids:
        analysis = analyses_data.get(ing_id)
        if analysis is None:
            continue
        if analysis.level not in ("t2", "t3", "t4"):
            continue
        for alt in analysis.alternatives or []:
            alternatives.append(
                AlternativeItem(
                    current_ingredient_id=ing_id,
                    better_ingredient_id=alt.get("better_ingredient_id", 0),
                    reason=alt.get("reason", ""),
                )
            )

    verdict: dict[str, Any] = {
        "level": product_analysis.level,
        "description": product_analysis.description,
    }

    return ProductAnalysisResult(
        source="db_cache",
        ingredients=ingredients,
        verdict=verdict,
        advice=product_analysis.advice,
        alternatives=alternatives,
        demographics=product_analysis.demographics or [],  # type: ignore[arg-type]
        scenarios=product_analysis.scenarios or [],          # type: ignore[arg-type]
        references=product_analysis.references or [],      # type: ignore[arg-type]
    )


async def assemble_from_agent_output(
    agent_output: dict[str, Any],
    matched_ids: list[int],
    ingredients_data: list[dict],
    analyses_data: dict[int, object],
) -> ProductAnalysisResult:
    """
    从 Agent 输出组装 ProductAnalysisResult。

    source = "agent_generated"
    - ingredients[]: 从 matched_ids 组装（填充 IngredientAnalysis level）
    - alternatives[]: 同上
    - verdict: {level, description} ← agent_output.verdict_level / verdict_description
    - advice ← agent_output.advice
    - demographics ← agent_output.demographics
    - scenarios ← agent_output.scenarios
    - references ← agent_output.references
    """
    # 构建 ingredient_map（按 id 索引）
    ingredient_map: dict[int, dict] = {d["id"]: d for d in ingredients_data}

    ingredients: list[IngredientItem] = []
    for ing_id in matched_ids:
        d = ingredient_map.get(ing_id)
        if d is None:
            continue
        analysis = analyses_data.get(ing_id)
        level = analysis.level if analysis else "unknown"
        function_types: list[str] = d.get("function_type") or []
        category = " · ".join(function_types)
        ingredients.append(
            IngredientItem(
                ingredient_id=ing_id,
                name=d["name"],
                category=category,
                level=level,
            )
        )

    # unmatched 成分 → level="unknown" 的占位条目
    unmatched_names: list[str] = agent_output.get("unmatched_ingredient_names", [])
    for name in unmatched_names:
        ingredients.append(
            IngredientItem(
                ingredient_id=0,
                name=name,
                category="",
                level="unknown",
            )
        )

    # 构建 alternatives（仅 level ∈ {t2, t3, t4}）
    alternatives: list[AlternativeItem] = []
    for ing_id in matched_ids:
        analysis = analyses_data.get(ing_id)
        if analysis is None:
            continue
        if analysis.level not in ("t2", "t3", "t4"):
            continue
        for alt in analysis.alternatives or []:
            alternatives.append(
                AlternativeItem(
                    current_ingredient_id=ing_id,
                    better_ingredient_id=alt.get("better_ingredient_id", 0),
                    reason=alt.get("reason", ""),
                )
            )

    verdict_level = agent_output.get("verdict_level", "t3")
    verdict_description = agent_output.get("verdict_description", "")

    verdict: dict[str, Any] = {
        "level": verdict_level,
        "description": verdict_description,
    }

    return ProductAnalysisResult(
        source="agent_generated",
        ingredients=ingredients,
        verdict=verdict,
        advice=agent_output.get("advice", ""),
        alternatives=alternatives,
        demographics=agent_output.get("demographics", []),
        scenarios=agent_output.get("scenarios", []),
        references=agent_output.get("references", []),
    )
