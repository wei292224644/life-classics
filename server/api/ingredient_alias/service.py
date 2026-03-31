"""Service layer for ingredient_alias."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db_repositories.ingredient_alias import IngredientAliasRepository


class IngredientAliasService:
    """配料别名服务."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = IngredientAliasRepository(session)

    async def create_alias(
        self,
        ingredient_id: int,
        alias: str,
        alias_type: str = "chinese",
    ) -> dict:
        """创建新别名."""
        new_alias = await self._repo.create(
            alias=alias,
            ingredient_id=ingredient_id,
            alias_type=alias_type,
        )
        await self._session.commit()
        return {
            "id": new_alias.id,
            "ingredient_id": new_alias.ingredient_id,
            "alias": new_alias.alias,
            "alias_type": new_alias.alias_type,
            "created_at": new_alias.created_at,
        }

    async def get_alias_by_id(self, alias_id: int) -> dict | None:
        """通过 ID 获取别名."""
        alias = await self._repo.find_by_id(alias_id)
        if alias is None:
            return None
        return {
            "id": alias.id,
            "ingredient_id": alias.ingredient_id,
            "alias": alias.alias,
            "alias_type": alias.alias_type,
            "created_at": alias.created_at,
        }

    async def list_aliases(self, ingredient_id: int | None = None) -> list[dict]:
        """列出别名，可按配料 ID 筛选."""
        if ingredient_id is not None:
            aliases = await self._repo.find_by_ingredient_id(ingredient_id)
        else:
            aliases = await self._repo.find_all()
        return [
            {
                "id": a.id,
                "ingredient_id": a.ingredient_id,
                "alias": a.alias,
                "alias_type": a.alias_type,
                "created_at": a.created_at,
            }
            for a in aliases
        ]

    async def delete_alias(self, alias_id: int) -> bool:
        """删除别名."""
        deleted = await self._repo.delete(alias_id)
        if deleted:
            await self._session.commit()
        return deleted
