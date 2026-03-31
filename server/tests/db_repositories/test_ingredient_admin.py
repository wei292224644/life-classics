"""Tests for IngredientAdminRepository."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

import pytest

from db_repositories.ingredient_admin import IngredientAdminRepository


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
    return m


class TestUpsert:
    @pytest.mark.asyncio
    async def test_creates_new_ingredient_when_not_exists(self):
        """按 name 不存在时，创建新配料."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # 不存在
        mock_session.execute.return_value = mock_result
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = IngredientAdminRepository(mock_session)
        result = await repo.upsert(name="蔗糖", description="食糖", is_additive=False)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_merges_existing_ingredient(self):
        """按 name 存在时，字段级合并."""
        existing = _mock_ingredient(name="蔗糖", id=1, description="初始", cas="57-50-1")
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = IngredientAdminRepository(mock_session)
        result = await repo.upsert(name="蔗糖", description="新描述")

        assert result.description == "新描述"
        assert result.cas == "57-50-1"  # 保留原有值


class TestFetchById:
    @pytest.mark.asyncio
    async def test_returns_ingredient_when_not_deleted(self):
        """未软删除的配料返回对象."""
        mock_ing = _mock_ingredient(id=1)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_ing
        mock_session.execute.return_value = mock_result

        repo = IngredientAdminRepository(mock_session)
        result = await repo.fetch_by_id(1)
        assert result == mock_ing

    @pytest.mark.asyncio
    async def test_returns_none_for_deleted(self):
        """软删除后返回 None."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = IngredientAdminRepository(mock_session)
        result = await repo.fetch_by_id(1)
        assert result is None


class TestSoftDelete:
    @pytest.mark.asyncio
    async def test_sets_deleted_at(self):
        """软删除设置 deleted_at."""
        mock_ing = _mock_ingredient(id=1)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_ing
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        repo = IngredientAdminRepository(mock_session)
        result = await repo.soft_delete(1)

        assert result is True
        assert mock_ing.deleted_at is not None

    @pytest.mark.asyncio
    async def test_idempotent_when_already_deleted(self):
        """重复删除返回 True（幂等）."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # 已删除
        mock_session.execute.return_value = mock_result

        repo = IngredientAdminRepository(mock_session)
        result = await repo.soft_delete(1)
        assert result is True