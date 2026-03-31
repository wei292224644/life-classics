"""Tests for food resolver."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from workflow_product_analysis.food_resolver import (
    InvalidFoodIdError,
    resolve_food_id,
)


class TestResolveFoodId:
    @pytest.mark.asyncio
    async def test_explicit_food_id_found(self):
        """explicit_food_id 存在 → 直接返回。"""
        mock_session = AsyncMock()
        mock_food = MagicMock()
        mock_food.id = 42
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_food
        mock_session.execute.return_value = mock_result

        result = await resolve_food_id(
            explicit_food_id=42,
            product_name=None,
            task_id="task-123",
            session=mock_session,
            settings=MagicMock(),
        )

        assert result == 42

    @pytest.mark.asyncio
    async def test_explicit_food_id_not_found_raises(self):
        """explicit_food_id 不存在 → InvalidFoodIdError。"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(InvalidFoodIdError):
            await resolve_food_id(
                explicit_food_id=999,
                product_name=None,
                task_id="task-123",
                session=mock_session,
                settings=MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_no_explicit_food_id_no_product_name_creates_placeholder(self):
        """无 explicit_food_id 且无 product_name → 创建占位 Food。"""
        mock_session = AsyncMock()
        # explicit_food_id is None → first execute returns None
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        # product_name is None → ILIKE branch skipped, scalars branch also returns None
        mock_result_empty = MagicMock()
        # scalars() creates fresh mock; configure scalars.return_value.all.return_value
        type(mock_result_empty).scalars = MagicMock(
            return_value=MagicMock(return_value=[])
        )
        mock_session.execute.side_effect = [mock_result_none]

        mock_settings = MagicMock()
        mock_settings.SYSTEM_USER_ID = "system-uuid"

        result = await resolve_food_id(
            explicit_food_id=None,
            product_name=None,
            task_id="task-xyz",
            session=mock_session,
            settings=mock_settings,
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.barcode == "PHOTO-task-xyz"
        assert added.name == "未命名产品"
