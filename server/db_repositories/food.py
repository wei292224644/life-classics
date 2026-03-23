from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import AnalysisDetail, Food, FoodIngredient, FoodNutritionEntry


@dataclass
class NutritionDetail:
    name: str
    alias: list[str]
    value: str
    value_unit: str
    reference_type: str
    reference_unit: str


@dataclass
class ProductIngredientAnalysisDetail:
    level: str
    reason: str | None


@dataclass
class ProductIngredientDetail:
    id: int
    name: str
    who_level: str | None
    function_type: str | None
    allergen_info: str | None
    analysis: "ProductIngredientAnalysisDetail | None"


@dataclass
class AnalysisSummary:
    id: int
    analysis_type: str
    results: dict
    level: str


@dataclass
class FoodDetail:
    id: int
    barcode: str
    name: str
    manufacturer: str | None
    origin_place: str | None
    shelf_life: str | None
    net_content: str | None
    image_url_list: list[str]
    nutritions: list[NutritionDetail]
    ingredients: list[ProductIngredientDetail]
    analysis: list[AnalysisSummary]


class FoodRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_by_barcode(self, barcode: str) -> FoodDetail | None:
        result = await self._session.execute(
            select(Food)
            .where(Food.barcode == barcode)
            .options(
                selectinload(Food.food_ingredients).selectinload(FoodIngredient.ingredient),
                selectinload(Food.food_nutrition_entries).selectinload(
                    FoodNutritionEntry.nutrition
                ),
            )
        )
        food = result.scalar_one_or_none()
        if food is None:
            return None

        # 查询 food 级别的 analysis (target_id == food.id and analysis_target == 'food')
        analysis_result = await self._session.execute(
            select(AnalysisDetail).where(
                AnalysisDetail.target_id == food.id,
                AnalysisDetail.analysis_target == "food",
            )
        )
        food_analyses = analysis_result.scalars().all()

        # 查询每个 ingredient 的 ingredient_summary analysis
        ingredient_ids = [fi.ingredient_id for fi in food.food_ingredients]
        ingredient_analysis_map: dict[int, AnalysisSummary | None] = {}
        if ingredient_ids:
            ing_analysis_result = await self._session.execute(
                select(AnalysisDetail).where(
                    AnalysisDetail.target_id.in_(ingredient_ids),
                    AnalysisDetail.analysis_target == "ingredient",
                    AnalysisDetail.analysis_type == "ingredient_summary",
                )
            )
            for a in ing_analysis_result.scalars().all():
                if a.target_id is not None:
                    ingredient_analysis_map[a.target_id] = AnalysisSummary(
                        id=a.id,
                        analysis_type=a.analysis_type,
                        results=a.results,
                        level=a.level,
                    )

        ingredients = []
        for fi in food.food_ingredients:
            ing_analysis = ingredient_analysis_map.get(fi.ingredient.id)
            if ing_analysis:
                # 提取 reason（从 results dict 中取，若无则 None）
                raw_results = ing_analysis.results
                reason = raw_results.get("reason") if isinstance(raw_results, dict) else None
                analysis = ProductIngredientAnalysisDetail(
                    level=ing_analysis.level,
                    reason=reason,
                )
            else:
                analysis = None

            ingredients.append(ProductIngredientDetail(
                id=fi.ingredient.id,
                name=fi.ingredient.name,
                who_level=fi.ingredient.who_level,
                function_type=fi.ingredient.function_type,
                allergen_info=fi.ingredient.allergen_info,
                analysis=analysis,
            ))

        nutritions = [
            NutritionDetail(
                name=fn.nutrition.name,
                alias=fn.nutrition.alias or [],
                value=str(fn.value),
                value_unit=fn.value_unit,
                reference_type=fn.reference_type,
                reference_unit=fn.reference_unit,
            )
            for fn in food.food_nutrition_entries
        ]

        analysis = [
            AnalysisSummary(
                id=a.id,
                analysis_type=a.analysis_type,
                results=a.results,
                level=a.level,
            )
            for a in food_analyses
        ]

        return FoodDetail(
            id=food.id,
            barcode=food.barcode,
            name=food.name,
            manufacturer=food.manufacturer,
            origin_place=food.origin_place,
            shelf_life=food.shelf_life,
            net_content=food.net_content,
            image_url_list=food.image_url_list or [],
            nutritions=nutritions,
            ingredients=ingredients,
            analysis=analysis,
        )
