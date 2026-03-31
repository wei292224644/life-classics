"""Tests for analysis API service functions (unit tests)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.analysis.service import (
    TaskNotFoundError,
    get_task_status,
    start_analysis,
)


class TestStartAnalysis:
    @pytest.mark.asyncio
    async def test_creates_task_and_returns_id(self):
        """start_analysis → creates Redis task and returns task_id。"""
        mock_redis = AsyncMock()
        mock_session = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ANALYSIS_TASK_TTL_SECONDS = 3600
        mock_settings.SYSTEM_USER_ID = "system-uuid"

        with patch(
            "api.analysis.service.create_task",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = {"task_id": "any"}

            with patch(
                "api.analysis.service.run_analysis_pipeline",
            ):
                task_id = await start_analysis(
                    image_bytes=b"fake",
                    food_id=None,
                    background_tasks=MagicMock(),
                    redis=mock_redis,
                    session=mock_session,
                    settings=mock_settings,
                )

        assert isinstance(task_id, str)
        mock_create.assert_called_once_with(mock_redis, task_id)


class TestGetTaskStatus:
    @pytest.mark.asyncio
    async def test_returns_task(self):
        """get_task_status → returns task dict。"""
        mock_redis = AsyncMock()
        mock_task = {"task_id": "t1", "status": "done", "error": None, "result": {}}

        with patch(
            "api.analysis.service.get_task",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = mock_task
            result = await get_task_status("t1", mock_redis)

        assert result == mock_task

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        """Task 不存在 → TaskNotFoundError。"""
        mock_redis = AsyncMock()

        with patch(
            "api.analysis.service.get_task",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = None
            with pytest.raises(TaskNotFoundError):
                await get_task_status("nonexistent", mock_redis)
