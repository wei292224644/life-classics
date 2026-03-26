"""测试 GET /api/product 端点（通过 patch service 层）。"""

import pytest
from unittest.mock import AsyncMock, patch

from db_repositories.food import (
    AnalysisSummary,
    FoodDetail,
    NutritionDetail,
    ProductIngredientDetail,
)
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
            who_level="Unknown",
            function_type=None,
            allergen_info="含麸质",
            analysis=None,
        )
    ],
    analysis=[
        AnalysisSummary(
            id=1,
            analysis_type="health_summary",
            result="普通零食",
            source="WHO评估报告",
            confidence_score=85,
            level="t1",
        )
    ],
)


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_product_found_returns_200():
    """存在的条形码返回 200 和完整数据。"""
    from api.product.service import ProductService

    mock_repo = AsyncMock()
    mock_repo.fetch_by_barcode.return_value = MOCK_FOOD

    svc = ProductService(mock_repo)
    result = await svc.get_product_by_barcode("6901234567890")

    assert result.barcode == "6901234567890"
    assert result.name == "测试饼干"


@pytest.mark.asyncio
async def test_product_not_found_raises_404():
    """条形码未收录时 service 抛出 ValueError。"""
    from api.product.service import ProductService

    mock_repo = AsyncMock()
    mock_repo.fetch_by_barcode.return_value = None

    svc = ProductService(mock_repo)
    with pytest.raises(ValueError, match="not_found"):
        await svc.get_product_by_barcode("0000000000000")


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
    assert response.ingredients[0].level.value == "unknown"
    # 精简版不应包含 full ingredient 的字段
    assert not hasattr(response.ingredients[0], "alias")
    assert not hasattr(response.ingredients[0], "is_additive")


def test_product_response_contains_analysis():
    """响应中包含 analysis 列表。"""
    from api.product.service import ProductService

    svc = ProductService(None)
    response = svc._to_product_response(MOCK_FOOD)

    assert len(response.analysis) == 1
    assert response.analysis[0].analysis_type == "health_summary"
    assert response.analysis[0].level == "t1"
