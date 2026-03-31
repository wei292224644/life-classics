"""Tests for IngredientAnalysis repository."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from db_repositories.ingredient_analysis import (
    get_active_by_ingredient_id,
    get_history_by_ingredient_id,
    insert_new_version,
)


class TestGetActiveByIngredientId:
    @pytest.mark.asyncio
    async def test_found(self):
        """Returns the active record when found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result

        result = await get_active_by_ingredient_id(1, mock_session)

        assert result is mock_record

    @pytest.mark.asyncio
    async def test_not_found(self):
        """Returns None when no active record."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await get_active_by_ingredient_id(999, mock_session)

        assert result is None


class TestInsertNewVersion:
    @pytest.mark.asyncio
    async def test_deactivates_old_and_inserts_new(self):
        """Deactivates existing active rows and inserts new active row."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # SQLAlchemy add() is sync

        data = {
            "ai_model": "claude",
            "version": "1.0",
            "level": "t1",
            "safety_info": "safe",
            "alternatives": [],
            "confidence_score": 0.9,
            "evidence_refs": [],
            "decision_trace": {},
        }

        await insert_new_version(5, data, "user-uuid", mock_session)

        mock_session.execute.assert_called_once()  # update deactivation
        mock_session.add.assert_called_once()       # new row added
        mock_session.flush.assert_called_once()

        added_record = mock_session.add.call_args[0][0]
        assert added_record.ingredient_id == 5
        assert added_record.ai_model == "claude"
        assert added_record.level == "t1"
        assert added_record.is_active is True


class TestGetHistoryByIngredientId:
    @pytest.mark.asyncio
    async def test_returns_ordered_list(self):
        """Returns all non-deleted versions ordered by created_at DESC."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_records = [MagicMock(), MagicMock()]
        mock_result.scalars.return_value.all.return_value = mock_records
        mock_session.execute.return_value = mock_result

        result = await get_history_by_ingredient_id(3, mock_session)

        assert result == mock_records
        mock_session.execute.assert_called_once()
