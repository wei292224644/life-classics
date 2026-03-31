"""Tests for ProductAnalysis repository."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db_repositories.product_analysis import ProductAnalysisRepository


class TestGetByFoodId:
    @pytest.mark.asyncio
    async def test_found(self):
        """Returns the record when found and not deleted."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_record = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result

        repo = ProductAnalysisRepository(mock_session)
        result = await repo.get_by_food_id(123)

        assert result is mock_record
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found(self):
        """Returns None when no active record exists."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ProductAnalysisRepository(mock_session)
        result = await repo.get_by_food_id(999)

        assert result is None


class TestInsertIfAbsent:
    @pytest.mark.asyncio
    async def test_inserts_new(self):
        """Returns (record, 'inserted') when no existing record."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        data = {
            "ai_model": "claude",
            "version": "1.0",
            "level": "t2",
            "description": "test",
            "advice": "eat less",
            "demographics": [],
            "scenarios": [],
            "references": [],
        }

        repo = ProductAnalysisRepository(mock_session)
        result, status = await repo.insert_if_absent(123, data, "user-uuid")

        assert status == "inserted"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_already_exists(self):
        """Returns (existing, 'already_exists') when record is found."""
        mock_session = AsyncMock()
        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        repo = ProductAnalysisRepository(mock_session)
        result, status = await repo.insert_if_absent(
            123,
            {"ai_model": "x", "version": "1", "level": "t0",
             "description": "", "advice": ""},
            "user-uuid",
        )

        assert result is mock_existing
        assert status == "already_exists"
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_unique_violation_rolls_back_and_reuses(self):
        """On UniqueViolation, re-fetches existing record."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.rollback = AsyncMock()
        mock_existing = MagicMock()

        # First execute (get_by_food_id before insert) returns None
        # Second execute (re-fetch after rollback) returns mock_existing
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_result_existing = MagicMock()
        mock_result_existing.scalar_one_or_none.return_value = mock_existing

        call_count = 0

        async def fake_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result_none
            return mock_result_existing

        mock_session.execute.side_effect = fake_execute

        repo = ProductAnalysisRepository(mock_session)
        mock_session.flush.side_effect = Exception("UniqueViolation")

        result, status = await repo.insert_if_absent(
            123,
            {"ai_model": "x", "version": "1", "level": "t0",
             "description": "", "advice": ""},
            "user-uuid",
        )

        assert result is mock_existing
        assert status == "already_exists"
        mock_session.rollback.assert_called_once()
