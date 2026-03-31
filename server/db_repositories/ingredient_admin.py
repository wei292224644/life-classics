from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Ingredient


class IngredientAdminRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

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
