from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Food, FoodIngredient, FoodNutritionEntry


@dataclass
class NutritionDetail:
    name: str
    alias: list[str]
    value: str
    value_unit: str
    reference_type: str
    reference_unit: str


@dataclass
class ProductIngredientDetail:
    id: int
    name: str
    who_level: str | None
    function_type: str | None
    allergen_info: str | None


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


class FoodRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_by_id(self, food_id: int) -> FoodDetail | None:
        result = await self._session.execute(
            select(Food)
            .where(Food.id == food_id, Food.deleted_at.is_(None))
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

        ingredients = [
            ProductIngredientDetail(
                id=fi.ingredient.id,
                name=fi.ingredient.name,
                who_level=fi.ingredient.who_level,
                function_type=fi.ingredient.function_type,
                allergen_info=fi.ingredient.allergen_info,
            )
            for fi in food.food_ingredients
        ]

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
        )

    async def fetch_by_id_simple(self, food_id: int) -> Food | None:
        """简单查询 Food（无关联加载），仅用于 existence check。"""
        result = await self._session.execute(
            select(Food).where(Food.id == food_id, Food.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def fetch_by_name_ilike(self, pattern: str) -> list[Food]:
        """模糊查询 Food，匹配 name ilike pattern，返回所有未删除的候选"""
        result = await self._session.execute(
            select(Food).where(
                Food.name.ilike(pattern),
                Food.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())
