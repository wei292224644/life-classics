from dataclasses import dataclass

from sqlalchemy import func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AnalysisDetail, Food, FoodIngredient, Ingredient


@dataclass
class FoodSearchResult:
    id: int
    barcode: str
    name: str
    product_category: str | None
    risk_level: str
    high_risk_count: int


@dataclass
class IngredientSearchResult:
    id: int
    name: str
    function_type: list[str]
    risk_level: str


class SearchRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search_foods(self, q: str) -> list[FoodSearchResult]:
        """按名称搜索食品，并附带 overall_risk 风险等级和高风险配料数。"""
        foods_result = await self._session.execute(
            select(Food.id, Food.barcode, Food.name, Food.product_category)
            .where(
                Food.name.ilike(f"%{q}%"),
                Food.deleted_at.is_(None),
            )
        )
        foods = foods_result.all()
        if not foods:
            return []

        food_ids = [f.id for f in foods]

        # 获取每个食品的 overall_risk 风险等级
        risk_result = await self._session.execute(
            select(AnalysisDetail.target_id, AnalysisDetail.level).where(
                AnalysisDetail.target_id.in_(food_ids),
                AnalysisDetail.analysis_target == "food",
                AnalysisDetail.analysis_type == "overall_risk",
            )
        )
        risk_map: dict[int, str] = {r.target_id: r.level for r in risk_result.all()}

        # 统计每个食品的高风险配料数（ingredient_summary level 为 t3 或 t4）
        high_risk_result = await self._session.execute(
            select(FoodIngredient.food_id, func.count().label("cnt"))
            .join(
                AnalysisDetail,
                (AnalysisDetail.target_id == FoodIngredient.ingredient_id)
                & (AnalysisDetail.analysis_target == "ingredient")
                & (AnalysisDetail.analysis_type == "ingredient_summary")
                & (AnalysisDetail.level.in_(["t3", "t4"])),
            )
            .where(FoodIngredient.food_id.in_(food_ids))
            .group_by(FoodIngredient.food_id)
        )
        high_risk_map: dict[int, int] = {r.food_id: r.cnt for r in high_risk_result.all()}

        return [
            FoodSearchResult(
                id=f.id,
                barcode=f.barcode,
                name=f.name,
                product_category=f.product_category,
                risk_level=risk_map.get(f.id, "unknown"),
                high_risk_count=high_risk_map.get(f.id, 0),
            )
            for f in foods
        ]

    async def search_ingredients(self, q: str) -> list[IngredientSearchResult]:
        """按名称或别名搜索配料，并附带 ingredient_summary 风险等级。"""
        ings_result = await self._session.execute(
            select(Ingredient.id, Ingredient.name, Ingredient.function_type).where(
                or_(
                    Ingredient.name.ilike(f"%{q}%"),
                    literal(q).op("= ANY")(Ingredient.alias),
                )
            )
        )
        ings = ings_result.all()
        if not ings:
            return []

        ing_ids = [i.id for i in ings]

        risk_result = await self._session.execute(
            select(AnalysisDetail.target_id, AnalysisDetail.level).where(
                AnalysisDetail.target_id.in_(ing_ids),
                AnalysisDetail.analysis_target == "ingredient",
                AnalysisDetail.analysis_type == "ingredient_summary",
            )
        )
        risk_map: dict[int, str] = {r.target_id: r.level for r in risk_result.all()}

        return [
            IngredientSearchResult(
                id=i.id,
                name=i.name,
                function_type=i.function_type or [],
                risk_level=risk_map.get(i.id, "unknown"),
            )
            for i in ings
        ]
