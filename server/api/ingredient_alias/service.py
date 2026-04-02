"""Service layer for ingredient_alias."""
from __future__ import annotations

from api.ingredient_alias.models import AliasResponse
from db_repositories.ingredient_alias import IngredientAliasRepository


class IngredientAliasService:
    """配料别名服务."""

    def __init__(self, repo: IngredientAliasRepository):
        self._repo = repo

    async def create_alias(
        self,
        ingredient_id: int,
        alias: str,
        alias_type: str = "chinese",
    ) -> AliasResponse:
        """创建新别名.

        Raises:
            ValueError: ingredient_id 不存在
            IntegrityError: alias 已存在
        """
        # 校验 ingredient_id 存在（通过 repo 层）
        exists = await self._repo.ingredient_exists(ingredient_id)
        if not exists:
            raise ValueError(f"ingredient_id={ingredient_id} not found")

        new_alias = await self._repo.create(
            alias=alias,
            ingredient_id=ingredient_id,
            alias_type=alias_type,
        )
        # 不 commit，事务由 router 层统一管理
        return AliasResponse.model_validate(new_alias)

    async def get_alias_by_id(self, alias_id: int) -> AliasResponse | None:
        """通过 ID 获取别名."""
        alias = await self._repo.find_by_id(alias_id)
        if alias is None:
            return None
        return AliasResponse.model_validate(alias)

    async def list_aliases(
        self, ingredient_id: int | None = None
    ) -> tuple[list[AliasResponse], int]:
        """列出别名，可按配料 ID 筛选. 返回 (items, total)."""
        if ingredient_id is not None:
            aliases = await self._repo.find_by_ingredient_id(ingredient_id)
        else:
            aliases = await self._repo.find_all()
        items = [AliasResponse.model_validate(a) for a in aliases]
        return items, len(items)

    async def delete_alias(self, alias_id: int) -> bool:
        """删除别名."""
        deleted = await self._repo.delete(alias_id)
        # 不 commit，事务由 router 层统一管理
        return deleted
