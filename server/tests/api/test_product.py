"""测试 GET /api/product/{food_id} 端点（通过 mock service 层）。"""

import pytest
from unittest.mock import AsyncMock

from db_repositories.food import FoodDetail, NutritionDetail, ProductIngredientDetail
from api.product.models import ProductResponse


# ── Mock Data ─────────────────────────────────────────────────────────────────

MOCK_FOOD = FoodDetail(
    id=1,
    barcode="6901234567890",
    name="测试饼干",
    manufacturer="测试食品有限公司",
    origin_place="中国",
    shelf_life="12个月",
    net_content="100g",
    image_url_list=[],
    nutritions=[
        NutritionDetail(
            name="能量",
            alias=[],
            value="2000.0000",
            value_unit="kJ",
            reference_type="PER_100_WEIGHT",
            reference_unit="g",
        )
    ],
    ingredients=[
        ProductIngredientDetail(
            id=1,
            name="小麦粉",
            who_level=None,
            function_type=None,
            allergen_info=None,
        )
    ],
)


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_product_found_returns_200():
    """存在的产品 ID 返回 200 和完整数据。"""
    from api.product.service import ProductService

    mock_repo = AsyncMock()
    mock_repo.fetch_by_id.return_value = MOCK_FOOD

    svc = ProductService(mock_repo)
    result = await svc.get_product_by_id(1)

    assert result.barcode == "6901234567890"
    assert result.name == "测试饼干"


@pytest.mark.asyncio
async def test_product_not_found_raises_404():
    """产品 ID 不存在时 service 抛出 ValueError。"""
    from api.product.service import ProductService

    mock_repo = AsyncMock()
    mock_repo.fetch_by_id.return_value = None

    svc = ProductService(mock_repo)
    with pytest.raises(ValueError, match="not_found"):
        await svc.get_product_by_id(999)


def test_product_response_contains_nutritions():
    """响应中包含 nutritions 列表。"""
    from api.product.service import ProductService

    svc = ProductService(None)
    response = svc._to_product_response(MOCK_FOOD)

    assert len(response.nutritions) == 1
    assert response.nutritions[0].name == "能量"
    assert response.nutritions[0].value_unit == "kJ"


def test_product_response_contains_ingredients():
    """响应中包含 ingredients 列表（精简版）。"""
    from api.product.service import ProductService

    svc = ProductService(None)
    response = svc._to_product_response(MOCK_FOOD)

    assert len(response.ingredients) == 1
    assert response.ingredients[0].name == "小麦粉"
    # 精简版只含 id 和 name
    assert not hasattr(response.ingredients[0], "who_level")
    assert not hasattr(response.ingredients[0], "function_type")
