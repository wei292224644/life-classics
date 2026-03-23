"""测试 GET /api/product 端点。"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.product.router import get_food_repository
from db_repositories.food import (
    AnalysisSummary,
    FoodDetail,
    NutritionDetail,
    ProductIngredientAnalysisDetail,
    ProductIngredientDetail,
)

# ── Mock Repository ───────────────────────────────────────────────────────────

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
            results={"summary": "普通零食"},
            level="t1",
        )
    ],
)


class FoundRepository:
    async def fetch_by_barcode(self, barcode: str):
        return MOCK_FOOD


class NotFoundRepository:
    async def fetch_by_barcode(self, barcode: str):
        return None


@pytest.fixture
def client_found():
    app.dependency_overrides[get_food_repository] = lambda: FoundRepository()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_not_found():
    app.dependency_overrides[get_food_repository] = lambda: NotFoundRepository()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Tests ────────────────────────────────────────────────────────────────────


def test_product_not_found_returns_404(client_not_found):
    """条形码未收录时返回 404。"""
    resp = client_not_found.get("/api/product?barcode=0000000000000")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Product not found"


def test_product_found_returns_200(client_found):
    """存在的条形码返回 200 和完整数据。"""
    resp = client_found.get("/api/product?barcode=6901234567890")
    assert resp.status_code == 200
    data = resp.json()
    assert data["barcode"] == "6901234567890"
    assert data["name"] == "测试饼干"


def test_product_response_contains_nutritions(client_found):
    """响应中包含 nutritions 列表。"""
    resp = client_found.get("/api/product?barcode=6901234567890")
    data = resp.json()
    assert len(data["nutritions"]) == 1
    assert data["nutritions"][0]["name"] == "能量"
    assert data["nutritions"][0]["value_unit"] == "kJ"


def test_product_response_contains_ingredients(client_found):
    """响应中包含 ingredients 列表。"""
    resp = client_found.get("/api/product?barcode=6901234567890")
    data = resp.json()
    assert len(data["ingredients"]) == 1
    assert data["ingredients"][0]["name"] == "小麦粉"
    assert data["ingredients"][0]["who_level"] == "Unknown"


def test_product_response_contains_analysis(client_found):
    """响应中包含 analysis 列表。"""
    resp = client_found.get("/api/product?barcode=6901234567890")
    data = resp.json()
    assert len(data["analysis"]) == 1
    assert data["analysis"][0]["analysis_type"] == "health_summary"
    assert data["analysis"][0]["level"] == "t1"


def test_missing_barcode_param_returns_422(client_not_found):
    """缺少 barcode 参数时返回 422。"""
    resp = client_not_found.get("/api/product")
    assert resp.status_code == 422
