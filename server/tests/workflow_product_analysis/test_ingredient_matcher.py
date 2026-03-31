import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from workflow_product_analysis.ingredient_matcher import (
    match_ingredients,
    normalize_ingredient_name,
)
from workflow_product_analysis.types import MatchResult

pytestmark = pytest.mark.asyncio


class TestNormalizeIngredientName:
    """预处理规则测试."""

    def test_remove_parentheses(self):
        assert normalize_ingredient_name("焦糖色（着色剂）") == "焦糖色"

    def test_english_lowercase(self):
        assert normalize_ingredient_name("SUCROSE") == "sucrose"

    def test_strip_whitespace(self):
        assert normalize_ingredient_name("  蔗糖  ") == "蔗糖"

    def test_remove_edible_prefix(self):
        assert normalize_ingredient_name("食用盐") == "盐"

    def test_combined(self):
        assert normalize_ingredient_name("  食用碳酸氢钠（小苏打）  ") == "碳酸氢钠"


class TestMatchIngredients:
    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    async def test_alias_match_success(self, mock_session):
        """别名匹配成功."""
        from database.models import IngredientAlias

        # Mock alias that matches "白砂糖" after normalization
        mock_alias = MagicMock()
        mock_alias.ingredient_id = 42
        mock_alias.alias = "白砂糖"
        mock_alias.normalized_alias = "白砂糖"

        # Mock ingredient result
        mock_ing = MagicMock()
        mock_ing.name = "蔗糖"
        mock_ing.function_type = []

        # Mock active analysis result - none
        mock_analysis = MagicMock()
        mock_analysis.scalar_one_or_none.return_value = None

        # Build mock result for IngredientAlias select (using scalar_one_or_none)
        mock_alias_result = MagicMock()
        mock_alias_result.scalar_one_or_none.return_value = mock_alias

        # Build mock result for Ingredient select
        mock_ing_result = MagicMock()
        mock_ing_result.scalar_one_or_none.return_value = mock_ing

        # Track call count to return different results
        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: find_by_normalized_alias does select(IngredientAlias)
                return mock_alias_result
            elif call_count[0] == 2:
                # Second call: fetch_ingredient_details does select(Ingredient)
                return mock_ing_result
            else:
                # Third call: get_active_by_ingredient_id
                return mock_analysis

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        result = await match_ingredients(["白砂糖"], mock_session)

        assert len(result["matched"]) == 1
        assert result["matched"][0]["ingredient_id"] == 42
        assert result["matched"][0]["name"] == "蔗糖"
        assert result["unmatched"] == []

    async def test_alias_unmatched(self, mock_session):
        """别名未命中."""
        # Mock result with no matching aliases (scalar_one_or_none returns None)
        mock_alias_result = MagicMock()
        mock_alias_result.scalar_one_or_none.return_value = None  # empty = no match

        async def mock_execute(query):
            return mock_alias_result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        result = await match_ingredients(["完全不存在的配料"], mock_session)
        assert result["unmatched"] == ["完全不存在的配料"]
        assert result["matched"] == []

    async def test_mixed_matches(self, mock_session):
        """混合场景：部分匹配成功."""
        # Mock alias for first ingredient
        mock_alias = MagicMock()
        mock_alias.ingredient_id = 42
        mock_alias.alias = "白砂糖"
        mock_alias.normalized_alias = "白砂糖"

        # Mock ingredient result
        mock_ing = MagicMock()
        mock_ing.name = "蔗糖"
        mock_ing.function_type = []

        mock_analysis = MagicMock()
        mock_analysis.scalar_one_or_none.return_value = None

        # Mock result for first ingredient (found via normalized_alias)
        mock_alias_result = MagicMock()
        mock_alias_result.scalar_one_or_none.return_value = mock_alias

        mock_ing_result = MagicMock()
        mock_ing_result.scalar_one_or_none.return_value = mock_ing

        # Mock result for second ingredient (no match)
        mock_alias_empty = MagicMock()
        mock_alias_empty.scalar_one_or_none.return_value = None

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] <= 3:
                # First ingredient: find_match calls:
                # 1. find_by_normalized_alias
                # 2. fetch_ingredient_details (select Ingredient)
                # 3. get_active_by_ingredient_id
                if call_count[0] == 1:
                    return mock_alias_result
                elif call_count[0] == 2:
                    return mock_ing_result
                else:
                    return mock_analysis
            else:
                # Second ingredient: find_by_normalized_alias returns empty
                return mock_alias_empty

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        result = await match_ingredients(["白砂糖", "不存在的配料"], mock_session)
        assert len(result["matched"]) == 1
        assert result["matched"][0]["name"] == "蔗糖"
        assert result["unmatched"] == ["不存在的配料"]

    async def test_empty_input(self, mock_session):
        """空输入."""
        result = await match_ingredients([], mock_session)
        assert result["matched"] == []
        assert result["unmatched"] == []
