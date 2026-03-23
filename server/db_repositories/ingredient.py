from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AnalysisDetail, Ingredient


@dataclass
class IngredientDetail:
    id: int
    name: str
    alias: list[str]
    is_additive: bool
    additive_code: str | None
    who_level: str | None
    allergen_info: str | None
    function_type: str | None
    standard_code: str | None
    analysis: dict | None  # first ingredient_summary analysis or None


class IngredientRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_by_id(self, ingredient_id: int) -> IngredientDetail | None:
        """通过配料 ID 查询配料详情（含 ingredient_summary 分析）。"""
        result = await self._session.execute(
            select(Ingredient).where(Ingredient.id == ingredient_id)
        )
        ingredient = result.scalar_one_or_none()
        if ingredient is None:
            return None

        # 查询 ingredient_summary 分析
        analysis_result = await self._session.execute(
            select(AnalysisDetail).where(
                AnalysisDetail.target_id == ingredient_id,
                AnalysisDetail.analysis_target == "ingredient",
                AnalysisDetail.analysis_type == "ingredient_summary",
            )
        )
        analyses = analysis_result.scalars().all()
        analysis_data: dict | None = None
        if analyses:
            a = analyses[0]
            analysis_data = {
                "id": a.id,
                "analysis_type": a.analysis_type,
                "results": a.results,
                "level": a.level,
            }

        return IngredientDetail(
            id=ingredient.id,
            name=ingredient.name,
            alias=ingredient.alias or [],
            is_additive=ingredient.is_additive or False,
            additive_code=ingredient.additive_code,
            who_level=ingredient.who_level,
            allergen_info=ingredient.allergen_info,
            function_type=ingredient.function_type,
            standard_code=ingredient.standard_code,
            analysis=analysis_data,
        )
