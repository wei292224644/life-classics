# server/tests/workflow_product_analysis/test_ingredient_alias.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from db_repositories.ingredient_alias import IngredientAliasRepository, normalize_ingredient_name
from database.models import Ingredient, IngredientAlias


class TestNormalizeIngredientName:
    def test_remove_parentheses(self):
        assert normalize_ingredient_name("焦糖色（着色剂）") == "焦糖色"
        assert normalize_ingredient_name("碳酸氢钠（小苏打）") == "碳酸氢钠"

    def test_english_lowercase(self):
        assert normalize_ingredient_name("SUCROSE") == "sucrose"
        assert normalize_ingredient_name("LECITHIN") == "lecithin"

    def test_strip_whitespace(self):
        assert normalize_ingredient_name("  蔗糖  ") == "蔗糖"

    def test_remove_edible_prefix(self):
        assert normalize_ingredient_name("食用盐") == "盐"


class TestIngredientAliasRepository:
    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    async def test_find_by_alias_found(self, mock_session):
        ingredient = Ingredient(name="蔗糖", alias=["白砂糖"], is_additive=False)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock execute to return the ingredient alias
        mock_result = MagicMock()
        mock_alias = MagicMock()
        mock_alias.ingredient_id = ingredient.id
        mock_result.scalar_one_or_none.return_value = mock_alias
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = IngredientAliasRepository(mock_session)
        result = await repo.find_by_alias("白砂糖")
        assert result is not None
        assert result.ingredient_id == ingredient.id

    async def test_find_by_alias_not_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = IngredientAliasRepository(mock_session)
        result = await repo.find_by_alias("不存在的别名")
        assert result is None

    async def test_find_by_ingredient_id(self, mock_session):
        ingredient = Ingredient(name="蔗糖", alias=[], is_additive=False)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock execute for two aliases
        mock_alias1 = MagicMock()
        mock_alias1.alias = "白砂糖"
        mock_alias1.alias_type = "chinese"
        mock_alias2 = MagicMock()
        mock_alias2.alias = "食糖"
        mock_alias2.alias_type = "chinese"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_alias1, mock_alias2]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = IngredientAliasRepository(mock_session)
        aliases = await repo.find_by_ingredient_id(ingredient.id)
        assert len(aliases) == 2

    async def test_create_alias(self, mock_session):
        ingredient = Ingredient(name="焦糖色", alias=[], is_additive=True)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        repo = IngredientAliasRepository(mock_session)
        new_alias = await repo.create(
            alias="焦糖色素",
            ingredient_id=ingredient.id,
            alias_type="chinese",
        )
        await mock_session.commit()

        assert new_alias.alias == "焦糖色素"
        assert new_alias.ingredient_id == ingredient.id
        mock_session.add.assert_called_once()

    async def test_find_by_normalized_alias(self, mock_session):
        """标准化后别名匹配."""
        ingredient = Ingredient(name="碳酸氢钠", alias=[], is_additive=True)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock execute to return the ingredient alias
        mock_result = MagicMock()
        mock_alias = MagicMock()
        mock_alias.ingredient_id = ingredient.id
        mock_alias.alias = "小苏打"  # 原始别名
        mock_result.scalars.return_value.all.return_value = [mock_alias]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = IngredientAliasRepository(mock_session)
        # 用标准化名称查询（去除括号）
        result = await repo.find_by_normalized_alias("小苏打")
        assert result is not None
        assert result.ingredient_id == ingredient.id

    async def test_delete_alias(self, mock_session):
        """删除别名."""
        ingredient = Ingredient(name="蔗糖", alias=[], is_additive=False)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock the ingredient with an ID
        mock_alias = MagicMock()
        mock_alias.id = 1
        mock_alias.ingredient_id = ingredient.id
        mock_alias.alias = "白砂糖"
        mock_alias.alias_type = "chinese"

        # Mock execute for delete and subsequent find
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_alias
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = MagicMock(return_value=mock_alias)

        repo = IngredientAliasRepository(mock_session)
        deleted = await repo.delete(1)
        await mock_session.commit()

        assert deleted is True
        # 验证删除后查询不到
        mock_result.scalar_one_or_none.return_value = None
        result = await repo.find_by_alias("白砂糖")
        assert result is None
