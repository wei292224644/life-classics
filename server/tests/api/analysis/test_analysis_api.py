"""Tests for analysis API router and AnalysisService (L2) unit tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.analysis_service import AnalysisService
from api.analysis.models import FeedbackRequest


class TestSubmitFeedback:
    """Test AnalysisService.submit_feedback (迁自 api/analysis/service.py)."""

    @pytest.mark.asyncio
    async def test_creates_feedback_record(self):
        """submit_feedback → 写入 AnalysisFeedback 并返回 accepted=True。"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # SQLAlchemy add() is sync
        mock_session.flush = AsyncMock()

        req = MagicMock()
        req.task_id = "task-123"
        req.food_id = 5
        req.category = "verdict_wrong"
        req.message = "结论不对"
        req.client_context = {"page": "result"}

        # Mock repos (unused by submit_feedback but required by constructor)
        mock_food_repo = MagicMock()
        mock_alias_repo = MagicMock()
        mock_ingredient_repo = MagicMock()
        mock_analysis_repo = MagicMock()
        mock_product_repo = MagicMock()
        mock_product_svc = MagicMock()

        svc = AnalysisService(
            food_repo=mock_food_repo,
            ingredient_alias_repo=mock_alias_repo,
            ingredient_repo=mock_ingredient_repo,
            ingredient_analysis_repo=mock_analysis_repo,
            product_analysis_repo=mock_product_repo,
            product_analysis_svc=mock_product_svc,
        )

        result = await svc.submit_feedback(
            session=mock_session,
            req=req,
            client_ip="127.0.0.1",
            user_agent="TestAgent/1.0",
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
