from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Food, FoodIngredient, Ingredient, IngredientAnalysis


@dataclass
class FoodSearchResult:
    id: int
    barcode: str
    name: str
    product_category: str | None
    image_url: str | None
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
        """按名称搜索食品，并附带高风险配料数。"""
        foods_result = await self._session.execute(
            select(Food.id, Food.barcode, Food.name, Food.product_category, Food.image_url_list)
            .where(
                Food.name.ilike(f"%{q}%"),
                Food.deleted_at.is_(None),
            )
        )
        foods = foods_result.all()
        if not foods:
            return []

        food_ids = [f.id for f in foods]

        # 统计每个食品的高风险配料数（通过 IngredientAnalysis.level）
        high_risk_result = await self._session.execute(
            select(FoodIngredient.food_id, func.count(func.distinct(FoodIngredient.ingredient_id)).label("cnt"))
            .join(
                IngredientAnalysis,
                IngredientAnalysis.ingredient_id == FoodIngredient.ingredient_id,
            )
            .where(
                FoodIngredient.food_id.in_(food_ids),
                FoodIngredient.deleted_at.is_(None),
                IngredientAnalysis.is_active.is_(True),
                IngredientAnalysis.level.in_(["t3", "t4"]),
            )
            .group_by(FoodIngredient.food_id)
        )
        high_risk_map: dict[int, int] = {r.food_id: r.cnt for r in high_risk_result.all()}

        return [
            FoodSearchResult(
                id=f.id,
                barcode=f.barcode,
                name=f.name,
                product_category=f.product_category,
                image_url=f.image_url_list[0] if f.image_url_list else None,
                risk_level="unknown",
                high_risk_count=high_risk_map.get(f.id, 0),
            )
            for f in foods
        ]

    async def search_ingredients(self, q: str) -> list[IngredientSearchResult]:
        """按名称搜索配料，并附带风险等级。"""
        ings_result = await self._session.execute(
            select(Ingredient.id, Ingredient.name, Ingredient.function_type).where(
                Ingredient.name.ilike(f"%{q}%")
            )
        )
        ings = ings_result.all()
        if not ings:
            return []

        ing_ids = [i.id for i in ings]

        risk_result = await self._session.execute(
            select(IngredientAnalysis.ingredient_id, IngredientAnalysis.level).where(
                IngredientAnalysis.ingredient_id.in_(ing_ids),
                IngredientAnalysis.is_active.is_(True),
            )
        )
        risk_map: dict[int, str] = {r.ingredient_id: r.level for r in risk_result.all()}

        return [
            IngredientSearchResult(
                id=i.id,
                name=i.name,
                function_type=i.function_type or [],
                risk_level=risk_map.get(i.id, "unknown"),
            )
            for i in ings
        ]
