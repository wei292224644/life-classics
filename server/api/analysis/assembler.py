"""结果组装器 — 将各阶段产物组装为 ProductAnalysisResult。"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db_repositories.ingredient_analysis import IngredientAnalysisRepository
from database.models import Ingredient, ProductAnalysis
from workflow_product_analysis.types import (
    AlternativeItem,
    IngredientItem,
    ProductAnalysisResult,
)

if TYPE_CHECKING:
    pass


async def _build_ingredients_list(
    matched_ids: list[int],
    session: AsyncSession,
) -> list[IngredientItem]:
    """
    根据 matched ingredient_ids 列表，从 DB 查询拼接 IngredientItem[]。
    每个条目的 category 来自 ingredient.function_type join。
    """
    if not matched_ids:
        return []

    result = await session.execute(
        select(Ingredient).where(Ingredient.id.in_(matched_ids))
    )
    ingredients = result.scalars().all()
    ingredient_map = {ing.id: ing for ing in ingredients}

    items: list[IngredientItem] = []
    for ing_id in matched_ids:
        ing = ingredient_map.get(ing_id)
        if ing is None:
            continue
        function_types: list[str] = ing.function_type or []
        category = " · ".join(function_types)
        items.append(
            IngredientItem(
                ingredient_id=ing.id,
                name=ing.name,
                category=category,
                level="unknown",  # level 从 IngredientAnalysis 填充，下方覆盖
            )
        )
    return items


async def _build_alternatives(
    matched_ids: list[int],
    repo: IngredientAnalysisRepository,
) -> list[AlternativeItem]:
    """
    仅处理 level ∈ {t2, t3, t4} 的成分：
    读取其 IngredientAnalysis.alternatives，转换为 AlternativeItem[]。
    """
    alternatives: list[AlternativeItem] = []
    for ing_id in matched_ids:
        analysis = await repo.get_active_by_ingredient_id(ing_id)
        if analysis is None:
            continue
        level = analysis.level
        if level not in ("t2", "t3", "t4"):
            continue
        for alt in analysis.alternatives or []:
            alternatives.append(
                AlternativeItem(
                    current_ingredient_id=ing_id,
                    better_ingredient_id=alt.get("better_ingredient_id", 0),
                    reason=alt.get("reason", ""),
                )
            )
    return alternatives


async def assemble_from_db_cache(
    product_analysis: ProductAnalysis,
    matched_ids: list[int],
    session: AsyncSession,
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
    ingredients = await _build_ingredients_list(matched_ids, session)
    analysis_repo = IngredientAnalysisRepository(session)

    # 填充 level（从 IngredientAnalysis）
    for item in ingredients:
        analysis = await analysis_repo.get_active_by_ingredient_id(item["ingredient_id"])
        if analysis is not None:
            item["level"] = analysis.level  # type: ignore[index]

    alternatives = await _build_alternatives(matched_ids, analysis_repo)

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
    session: AsyncSession,
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
    ingredients = await _build_ingredients_list(matched_ids, session)
    analysis_repo = IngredientAnalysisRepository(session)

    # 填充 level
    for item in ingredients:
        analysis = await analysis_repo.get_active_by_ingredient_id(item["ingredient_id"])
        if analysis is not None:
            item["level"] = analysis.level  # type: ignore[index]

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

    alternatives = await _build_alternatives(matched_ids, analysis_repo)

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
