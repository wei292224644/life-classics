"""E2E tests for ingredients CRUD API."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app as cors_app
from api.ingredients.router import get_repo

# The exported app is CORSMiddleware; access the inner FastAPI app for dependency overrides
app = cors_app.app


def _mock_ingredient(name="测试配料", id=1, deleted_at=None, **kwargs):
    """创建模拟 Ingredient 对象."""
    m = MagicMock()
    m.name = name
    m.id = id
    m.deleted_at = deleted_at
    m.description = kwargs.get("description")
    m.is_additive = kwargs.get("is_additive", False)
    m.additive_code = kwargs.get("additive_code")
    m.standard_code = kwargs.get("standard_code")
    m.who_level = kwargs.get("who_level")
    m.allergen_info = kwargs.get("allergen_info", [])
    m.function_type = kwargs.get("function_type", [])
    m.origin_type = kwargs.get("origin_type")
    m.limit_usage = kwargs.get("limit_usage")
    m.legal_region = kwargs.get("legal_region")
    m.cas = kwargs.get("cas")
    m.applications = kwargs.get("applications")
    m.notes = kwargs.get("notes")
    m.safety_info = kwargs.get("safety_info")
    m.alias = kwargs.get("alias", [])
    return m


def _make_mock_repo(**methods):
    """创建配置了指定方法的 mock repo."""
    mock = AsyncMock()
    for name, value in methods.items():
        setattr(mock, name, AsyncMock(return_value=value))
    return mock


class TestCreateIngredient:
    @pytest.mark.asyncio
    async def test_create_returns_201(self):
        """创建新配料返回 201."""
        mock_ing = _mock_ingredient(id=1, name="蔗糖", description="食糖")
        mock_repo = _make_mock_repo(upsert=mock_ing)

        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/ingredients", json={"name": "蔗糖", "description": "食糖"})

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "蔗糖"
        finally:
            app.dependency_overrides.clear()


class TestGetIngredient:
    @pytest.mark.asyncio
    async def test_get_ingredient_returns_200(self):
        """获取配料返回 200."""
        mock_ing = _mock_ingredient(id=1, name="蔗糖")
        mock_repo = _make_mock_repo(fetch_by_id=mock_ing)

        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/ingredients/1")

            assert response.status_code == 200
            assert response.json()["name"] == "蔗糖"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_ingredient_returns_404_when_not_found(self):
        """配料不存在返回 404."""
        mock_repo = _make_mock_repo(fetch_by_id=None)

        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/ingredients/999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestListIngredients:
    @pytest.mark.asyncio
    async def test_list_returns_200(self):
        """列表查询返回 200."""
        mock_ings = [_mock_ingredient(id=1, name="蔗糖"), _mock_ingredient(id=2, name="白砂糖")]
        mock_repo = _make_mock_repo(fetch_list=(mock_ings, 2))

        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/ingredients")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.clear()


class TestUpdateIngredient:
    @pytest.mark.asyncio
    async def test_update_partial_returns_200(self):
        """部分更新返回 200."""
        mock_ing = _mock_ingredient(id=1, name="蔗糖", description="更新后")
        mock_repo = _make_mock_repo(update_partial=mock_ing)

        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.patch("/api/ingredients/1", json={"description": "更新后"})

            assert response.status_code == 200
            assert response.json()["description"] == "更新后"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_full_returns_200(self):
        """全量更新返回 200."""
        mock_ing = _mock_ingredient(id=1, name="蔗糖", description="全量更新")
        mock_repo = _make_mock_repo(update_full=mock_ing)

        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.put("/api/ingredients/1", json={
                    "name": "蔗糖",
                    "description": "全量更新",
                    "is_additive": False,
                    "allergen_info": [],
                    "function_type": [],
                })

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestDeleteIngredient:
    @pytest.mark.asyncio
    async def test_delete_returns_204(self):
        """删除返回 204."""
        mock_repo = _make_mock_repo(soft_delete=True)

        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete("/api/ingredients/1")

            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()
