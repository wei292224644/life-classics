"""配料别名仓库 — 别名精确匹配的核心逻辑."""
from __future__ import annotations

import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import IngredientAlias


def normalize_ingredient_name(name: str) -> str:
    """
    标准化配料名称。

    规则：
    - 去除括号内容（含括号）："焦糖色（着色剂）" → "焦糖色"
    - 英文转小写："SUCROSE" → "sucrose"
    - 去除首尾空格："  蔗糖  " → "蔗糖"
    - 去除"食用"前缀："食用盐" → "盐"
    """
    if not name:
        return name

    result = name.strip()

    # 去除括号内容
    result = re.sub(r"[（(].*?[)）]", "", result)

    # 去除"食用"前缀
    if result.startswith("食用"):
        result = result[2:]

    # 英文转小写
    result = result.lower()

    # 去除多余空格
    result = re.sub(r"\s+", " ", result).strip()

    return result


class IngredientAliasRepository:
    """配料别名仓库."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_alias(self, alias: str) -> IngredientAlias | None:
        """按别名精确查询."""
        result = await self._session.execute(
            select(IngredientAlias).where(IngredientAlias.alias == alias)
        )
        return result.scalar_one_or_none()

    async def find_by_normalized_alias(self, normalized_alias: str) -> IngredientAlias | None:
        """
        按标准化后的别名查询。

        注意：alias 列存储的是原始别名（非标准化后），
        查询时需要遍历匹配。
        """
        normalized_target = normalize_ingredient_name(normalized_alias)
        result = await self._session.execute(select(IngredientAlias))
        for row in result.scalars().all():
            if normalize_ingredient_name(row.alias) == normalized_target:
                return row
        return None

    async def find_by_ingredient_id(self, ingredient_id: int) -> list[IngredientAlias]:
        """按配料 ID 查询所有别名."""
        result = await self._session.execute(
            select(IngredientAlias).where(IngredientAlias.ingredient_id == ingredient_id)
        )
        return list(result.scalars().all())

    async def create(
        self,
        alias: str,
        ingredient_id: int,
        alias_type: str = "chinese",
    ) -> IngredientAlias:
        """创建新别名."""
        new_alias = IngredientAlias(
            alias=alias,
            ingredient_id=ingredient_id,
            alias_type=alias_type,
        )
        self._session.add(new_alias)
        await self._session.flush()
        return new_alias

    async def delete(self, alias_id: int) -> bool:
        """删除别名，返回是否删除成功."""
        result = await self._session.execute(
            select(IngredientAlias).where(IngredientAlias.id == alias_id)
        )
        alias = result.scalar_one_or_none()
        if alias is None:
            return False
        await self._session.delete(alias)
        return True