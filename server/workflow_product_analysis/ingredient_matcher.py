"""组件 3：成分匹配 — 将成分名通过别名精确匹配到配料库。"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db_repositories.ingredient_alias import (
    IngredientAliasRepository,
    normalize_ingredient_name,
)
from db_repositories.ingredient_analysis import IngredientAnalysisRepository
from database.models import Ingredient
from workflow_product_analysis.types import (
    IngredientRiskLevel,
    MatchedIngredient,
    MatchResult,
)

if TYPE_CHECKING:
    pass


async def match_ingredients(
    ingredient_names: list[str],
    session: AsyncSession,
) -> MatchResult:
    """
    将成分名列表通过别名精确匹配到配料库（ingredients 表）。

    入参：
        ingredient_names: 原始成分名列表（来自 OCR 解析）
        session: AsyncSession

    出参：
        MatchResult: {matched: [...], unmatched: [...]}：
        - matched: 匹配成功的成分（含 ingredient_id、name、level）
        - unmatched: 匹配失败的原始成分名
    """
    if not ingredient_names:
        return MatchResult(matched=[], unmatched=[])

    repo = IngredientAliasRepository(session)

    async def find_match(name: str) -> tuple[str, MatchedIngredient | None]:
        normalized = normalize_ingredient_name(name)
        alias_record = await repo.find_by_normalized_alias(normalized)

        if alias_record is None:
            return name, None

        ingredient_id = alias_record.ingredient_id
        details = await fetch_ingredient_details(ingredient_id, session)
        if details is None:
            return name, None

        name_db, category_str, level = details
        return name, MatchedIngredient(
            ingredient_id=ingredient_id,
            name=name_db,
            level=level,
        )

    results = await asyncio.gather(*[find_match(name) for name in ingredient_names])

    matched = [m for _, m in results if m is not None]
    unmatched = [name for name, m in results if m is None]

    return MatchResult(matched=matched, unmatched=unmatched)


async def fetch_ingredient_details(
    ingredient_id: int,
    session: AsyncSession,
) -> tuple[str, str, IngredientRiskLevel] | None:
    """
    按 ingredient_id 查 DB，返回 (name, category_str, level)。

    category_str: function_type 数组拼接，如 "增稠剂 · 高升糖指数"
    level: 来自 active IngredientAnalysis；无记录则返回 "unknown"
    """
    result = await session.execute(
        select(Ingredient).where(Ingredient.id == ingredient_id)
    )
    ingredient = result.scalar_one_or_none()

    if ingredient is None:
        return None

    function_types: list[str] = ingredient.function_type or []
    category_str = " · ".join(function_types)

    analysis_repo = IngredientAnalysisRepository(session)
    analysis = await analysis_repo.get_active_by_ingredient_id(ingredient_id)
    if analysis is not None:
        level: IngredientRiskLevel = analysis.level
    else:
        level = "unknown"

    return ingredient.name, category_str, level