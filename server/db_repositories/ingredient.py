from datetime import datetime, UTC
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AnalysisDetail, Ingredient, Food, FoodIngredient


@dataclass
class IngredientDetail:
    id: int
    name: str
    alias: list[str]
    description: str | None
    is_additive: bool
    additive_code: str | None
    standard_code: str | None
    who_level: str | None
    allergen_info: list[str]
    function_type: list[str]
    origin_type: str | None
    limit_usage: str | None
    legal_region: str | None
    cas: str | None
    applications: str | None
    notes: str | None
    safety_info: str | None
    analyses: list[dict]  # 所有分析类型的原始记录
    related_products: list[dict]  # [{id, name, barcode, image_url, category}]


class IngredientRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    # ─── 管理端写操作（原 IngredientAdminRepository） ─────────────────────────

    async def upsert(self, **fields) -> Ingredient:
        """
        Upsert：按 name 精确匹配，存在则字段级合并，不存在则新建。
        空列表 [] 不覆盖已有值。
        """
        name = fields.pop("name")
        result = await self._session.execute(
            select(Ingredient).where(Ingredient.name == name, Ingredient.deleted_at.is_(None))
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            for key, value in fields.items():
                if value is not None and value != []:
                    setattr(existing, key, value)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        else:
            ingredient = Ingredient(name=name, **fields)
            self._session.add(ingredient)
            await self._session.commit()
            await self._session.refresh(ingredient)
            return ingredient

    async def fetch_by_id(self, ingredient_id: int) -> Ingredient | None:
        """获取单个配料，软删除的返回 None."""
        result = await self._session.execute(
            select(Ingredient).where(
                Ingredient.id == ingredient_id,
                Ingredient.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def fetch_list(
        self,
        limit: int = 20,
        offset: int = 0,
        name: str | None = None,
        is_additive: bool | None = None,
    ) -> tuple[list[Ingredient], int]:
        """分页查询配料列表."""
        query = select(Ingredient).where(Ingredient.deleted_at.is_(None))
        count_query = select(Ingredient.id).where(Ingredient.deleted_at.is_(None))

        if name is not None:
            query = query.where(Ingredient.name.ilike(f"%{name}%"))
            count_query = count_query.where(Ingredient.name.ilike(f"%{name}%"))

        if is_additive is not None:
            query = query.where(Ingredient.is_additive == is_additive)
            count_query = count_query.where(Ingredient.is_additive == is_additive)

        total_result = await self._session.execute(count_query)
        total = len(total_result.scalars().all())

        query = query.offset(offset).limit(limit)
        result = await self._session.execute(query)
        ingredients = result.scalars().all()

        return list(ingredients), total

    async def update_full(self, ingredient_id: int, **fields) -> Ingredient | None:
        """全量更新：所有字段使用请求值，未传字段置 None."""
        ingredient = await self.fetch_by_id(ingredient_id)
        if ingredient is None:
            return None
        for key, value in fields.items():
            setattr(ingredient, key, value)
        await self._session.commit()
        await self._session.refresh(ingredient)
        return ingredient

    async def update_partial(self, ingredient_id: int, **fields) -> Ingredient | None:
        """部分更新：只更新提供的非空字段."""
        ingredient = await self.fetch_by_id(ingredient_id)
        if ingredient is None:
            return None
        for key, value in fields.items():
            if value is not None and value != []:
                setattr(ingredient, key, value)
        await self._session.commit()
        await self._session.refresh(ingredient)
        return ingredient

    async def soft_delete(self, ingredient_id: int) -> bool:
        """软删除，幂等（已删除返回 True）."""
        ingredient = await self.fetch_by_id(ingredient_id)
        if ingredient is None:
            return True  # 幂等，已删除视为成功
        ingredient.deleted_at = datetime.now(UTC)
        await self._session.commit()
        return True

    # ─── 分析端读操作（原 IngredientRepository） ───────────────────────────────

    async def fetch_detail_by_id(self, ingredient_id: int) -> IngredientDetail | None:
        """通过配料 ID 查询配料详情（含所有分析）。"""
        result = await self._session.execute(
            select(Ingredient).where(Ingredient.id == ingredient_id)
        )
        ingredient = result.scalar_one_or_none()
        if ingredient is None:
            return None

        # 查询该配料所有分析（不限 analysis_type）
        analysis_result = await self._session.execute(
            select(AnalysisDetail).where(
                AnalysisDetail.target_id == ingredient_id,
                AnalysisDetail.analysis_target == "ingredient",
            )
        )
        analyses_data = [
            {
                "analysis_type": a.analysis_type,
                "result": a.result,
                "source": a.source,
                "level": a.level,
                "confidence_score": a.confidence_score,
            }
            for a in analysis_result.scalars().all()
        ]

        # 查询关联产品（通过 FoodIngredient -> Food）
        food_query = (
            select(Food.id, Food.name, Food.barcode, Food.image_url_list, Food.product_category)
            .join(FoodIngredient, FoodIngredient.food_id == Food.id)
            .where(FoodIngredient.ingredient_id == ingredient_id)
            .limit(6)
        )
        food_result = await self._session.execute(food_query)
        related_products = [
            {
                "id": row.id,
                "name": row.name,
                "barcode": row.barcode,
                "image_url": row.image_url_list[0] if row.image_url_list else None,
                "category": row.product_category,
            }
            for row in food_result.all()
        ]

        return IngredientDetail(
            id=ingredient.id,
            name=ingredient.name,
            alias=ingredient.alias or [],
            description=ingredient.description,
            is_additive=ingredient.is_additive or False,
            additive_code=ingredient.additive_code,
            standard_code=ingredient.standard_code,
            who_level=ingredient.who_level,
            allergen_info=ingredient.allergen_info or [],
            function_type=ingredient.function_type or [],
            origin_type=ingredient.origin_type,
            limit_usage=ingredient.limit_usage,
            legal_region=ingredient.legal_region,
            cas=ingredient.cas,
            applications=ingredient.applications,
            notes=ingredient.notes,
            safety_info=ingredient.safety_info,
            analyses=analyses_data,
            related_products=related_products,
        )
