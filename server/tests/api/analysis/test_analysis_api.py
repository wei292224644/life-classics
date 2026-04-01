"""Tests for analysis API service functions (unit tests)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.analysis.service import (
    FeedbackResponse,
    start_analysis,
    submit_feedback,
)


class TestStartAnalysis:
    @pytest.mark.asyncio
    async def test_creates_task_and_returns_id(self):
        """start_analysis → 调度后台任务并返回 task_id。"""
        mock_session = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.SYSTEM_USER_ID = "system-uuid"

        background_tasks_mock = MagicMock()
        background_tasks_mock.add_task = MagicMock()

        with patch(
            "api.analysis.service.run_analysis_in_background",
        ):
            task_id = await start_analysis(
                image_bytes=b"fake",
                food_id=None,
                background_tasks=background_tasks_mock,
                session=mock_session,
                settings=mock_settings,
            )

        assert isinstance(task_id, str)
        assert len(task_id) == 36  # UUID format
        background_tasks_mock.add_task.assert_called_once()


class TestSubmitFeedback:
    @pytest.mark.asyncio
    async def test_creates_feedback_record(self):
        """submit_feedback → 写入 AnalysisFeedback 并返回 accepted=True。"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # SQLAlchemy add() is sync
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "TestAgent/1.0"

        mock_req = MagicMock()
        mock_req.task_id = "task-123"
        mock_req.food_id = 5
        mock_req.category = "verdict_wrong"
        mock_req.message = "结论不对"
        mock_req.client_context = {"page": "result"}

        result = await submit_feedback(
            req=mock_req,
            request=mock_request,
            session=mock_session,
        )

        assert result.accepted is True
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

        added_record = mock_session.add.call_args[0][0]
        assert added_record.task_id == "task-123"
        assert added_record.food_id == 5
        assert added_record.category == "verdict_wrong"
        # IP hash should be SHA256 hex
        assert len(added_record.source_ip_hash) == 64
        # UA truncated to 512
        assert len(added_record.user_agent) <= 512
