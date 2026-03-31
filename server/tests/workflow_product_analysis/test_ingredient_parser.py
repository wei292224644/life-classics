import pytest
from unittest.mock import MagicMock, patch

from workflow_product_analysis.ingredient_parser import (
    parse_ingredients, NoIngredientsFoundError, IngredientParseOutput
)


class MockSettings:
    DEFAULT_LLM_PROVIDER = "anthropic"
    DEFAULT_MODEL = "MiniMax-2.7"


@pytest.fixture
def settings():
    return MockSettings()


@pytest.mark.asyncio
async def test_parse_ingredients_returns_list(settings):
    mock_output = IngredientParseOutput(
        ingredients=["燕麦粉", "麦芽糊精", "阿斯巴甜"],
        product_name="某某燕麦饼干"
    )
    # get_structured_client 返回同步 callable，mock 为普通 MagicMock
    mock_create_fn = MagicMock(return_value=mock_output)
    with patch(
        "workflow_product_analysis.ingredient_parser.get_structured_client",
        return_value=mock_create_fn,
    ):
        result = await parse_ingredients("配料：燕麦粉，麦芽糊精，阿斯巴甜（甜味剂）", settings)
        assert result.ingredients == ["燕麦粉", "麦芽糊精", "阿斯巴甜"]
        assert result.product_name == "某某燕麦饼干"


@pytest.mark.asyncio
async def test_parse_ingredients_empty_raises(settings):
    mock_output = IngredientParseOutput(ingredients=[], product_name=None)
    mock_create_fn = MagicMock(return_value=mock_output)
    with patch(
        "workflow_product_analysis.ingredient_parser.get_structured_client",
        return_value=mock_create_fn,
    ):
        with pytest.raises(NoIngredientsFoundError):
            await parse_ingredients("某段无配料表的文字", settings)


@pytest.mark.asyncio
async def test_parse_ingredients_no_product_name(settings):
    mock_output = IngredientParseOutput(ingredients=["白砂糖"], product_name=None)
    mock_create_fn = MagicMock(return_value=mock_output)
    with patch(
        "workflow_product_analysis.ingredient_parser.get_structured_client",
        return_value=mock_create_fn,
    ):
        result = await parse_ingredients("配料：白砂糖", settings)
        assert result.product_name is None
