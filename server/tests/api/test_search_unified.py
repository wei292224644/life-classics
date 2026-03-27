"""测试 UnifiedSearchService 的业务逻辑（mock SearchRepository）。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.search.service import UnifiedSearchService
from db_repositories.search import FoodSearchResult, IngredientSearchResult


MOCK_FOODS = [
    FoodSearchResult(id=1, barcode="111", name="测试饼干", product_category="饼干", image_url=None, risk_level="t2", high_risk_count=1),
    FoodSearchResult(id=2, barcode="222", name="测试糖果", product_category=None, image_url=None, risk_level="unknown", high_risk_count=0),
]

MOCK_INGREDIENTS = [
    IngredientSearchResult(id=10, name="苯甲酸钠", function_type=["防腐剂"], risk_level="t4"),
    IngredientSearchResult(id=11, name="色素红40", function_type=["着色剂", "稳定剂"], risk_level="t3"),
]


@pytest.mark.asyncio
async def test_search_all_combines_products_first_then_ingredients():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS
    mock_repo.search_ingredients.return_value = MOCK_INGREDIENTS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="all", offset=0, limit=20)

    assert result.total == 4
    assert result.items[0].type == "product"
    assert result.items[1].type == "product"
    assert result.items[2].type == "ingredient"
    assert result.items[3].type == "ingredient"
    assert result.has_more is False


@pytest.mark.asyncio
async def test_search_product_only_skips_ingredients():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="product", offset=0, limit=20)

    mock_repo.search_ingredients.assert_not_called()
    assert result.total == 2
    assert all(item.type == "product" for item in result.items)


@pytest.mark.asyncio
async def test_search_ingredient_only_skips_foods():
    mock_repo = AsyncMock()
    mock_repo.search_ingredients.return_value = MOCK_INGREDIENTS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="苯甲", result_type="ingredient", offset=0, limit=20)

    mock_repo.search_foods.assert_not_called()
    assert result.total == 2
    assert all(item.type == "ingredient" for item in result.items)


@pytest.mark.asyncio
async def test_search_pagination_has_more_true():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS
    mock_repo.search_ingredients.return_value = MOCK_INGREDIENTS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="all", offset=0, limit=2)

    assert result.total == 4
    assert len(result.items) == 2
    assert result.has_more is True
    assert result.offset == 0
    assert result.limit == 2


@pytest.mark.asyncio
async def test_search_last_page_has_more_false():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS
    mock_repo.search_ingredients.return_value = MOCK_INGREDIENTS

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="all", offset=2, limit=2)

    assert result.total == 4
    assert len(result.items) == 2
    assert result.has_more is False


@pytest.mark.asyncio
async def test_search_offset_beyond_total_returns_empty():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = MOCK_FOODS
    mock_repo.search_ingredients.return_value = []

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="测试", result_type="all", offset=100, limit=20)

    assert result.total == 2
    assert result.items == []
    assert result.has_more is False


@pytest.mark.asyncio
async def test_search_high_risk_count_none_when_zero():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = [
        FoodSearchResult(id=2, barcode="222", name="测试糖果", product_category=None, image_url=None, risk_level="unknown", high_risk_count=0),
    ]
    mock_repo.search_ingredients.return_value = []

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="糖果", result_type="all")

    assert result.items[0].highRiskCount is None


@pytest.mark.asyncio
async def test_search_high_risk_count_set_when_nonzero():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = [
        FoodSearchResult(id=1, barcode="111", name="测试饼干", product_category="饼干", image_url=None, risk_level="t2", high_risk_count=3),
    ]
    mock_repo.search_ingredients.return_value = []

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="饼干", result_type="all")

    assert result.items[0].highRiskCount == 3


@pytest.mark.asyncio
async def test_search_ingredient_subtitle_joined_with_slash():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = []
    mock_repo.search_ingredients.return_value = [
        IngredientSearchResult(id=11, name="色素红40", function_type=["着色剂", "稳定剂"], risk_level="t3"),
    ]

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="色素", result_type="all")

    assert result.items[0].subtitle == "着色剂/稳定剂"


@pytest.mark.asyncio
async def test_search_ingredient_empty_function_type_gives_empty_subtitle():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = []
    mock_repo.search_ingredients.return_value = [
        IngredientSearchResult(id=12, name="水", function_type=[], risk_level="t0"),
    ]

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="水", result_type="all")

    assert result.items[0].subtitle == ""


@pytest.mark.asyncio
async def test_search_product_barcode_included():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = [
        FoodSearchResult(id=1, barcode="6920152420245", name="可口可乐", product_category="碳酸饮料", image_url=None, risk_level="unknown", high_risk_count=0),
    ]
    mock_repo.search_ingredients.return_value = []

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="可口可乐", result_type="all")

    assert result.items[0].barcode == "6920152420245"


@pytest.mark.asyncio
async def test_search_product_no_barcode_on_ingredient():
    mock_repo = AsyncMock()
    mock_repo.search_foods.return_value = []
    mock_repo.search_ingredients.return_value = [
        IngredientSearchResult(id=10, name="苯甲酸钠", function_type=["防腐剂"], risk_level="t4"),
    ]

    svc = UnifiedSearchService(mock_repo)
    result = await svc.search(q="苯甲", result_type="all")

    assert result.items[0].barcode is None