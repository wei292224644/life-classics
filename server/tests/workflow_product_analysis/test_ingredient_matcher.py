"""Tests for ingredient matcher."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_product_analysis.ingredient_matcher import (
    _parse_ingredient_chunk_id,
    fetch_ingredient_details,
    match_ingredients,
)


class TestParseIngredientChunkId:
    def test_valid(self):
        assert _parse_ingredient_chunk_id("ingredient_42") == 42
        assert _parse_ingredient_chunk_id("ingredient_1") == 1

    def test_invalid(self):
        assert _parse_ingredient_chunk_id("foo_42") is None
        assert _parse_ingredient_chunk_id("ingredient_abc") is None
        assert _parse_ingredient_chunk_id("") is None


class TestMatchIngredients:
    @pytest.mark.asyncio
    async def test_high_similarity_matched(self):
        """Below threshold → matched."""
        mock_session = AsyncMock()
        mock_ing = MagicMock()
        mock_ing.name = "阿斯巴甜"
        mock_ing.function_type = ["甜味剂"]
        mock_analysis = MagicMock()
        mock_analysis.level = "t2"
        mock_result_ing = MagicMock()
        mock_result_ing.scalar_one_or_none.return_value = mock_ing
        mock_result_analysis = MagicMock()
        mock_result_analysis.scalar_one_or_none.return_value = mock_analysis
        mock_session.execute.side_effect = [mock_result_ing, mock_result_analysis]

        mock_settings = MagicMock()
        mock_settings.INGREDIENT_MATCH_THRESHOLD = 0.8

        async def fake_embed(batches, **kw):
            return [[0.1, 0.2]]

        async def fake_query(name, emb, top_k):
            # Returns list of (chunk_id, distance) — distance < threshold → matched
            return [("ingredient_5", 0.05)]

        with patch(
            "workflow_product_analysis.ingredient_matcher.embed_batch", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.side_effect = fake_embed
            with patch(
                "workflow_product_analysis.ingredient_matcher._query_ingredient_collection",
                new_callable=AsyncMock,
            ) as mock_q:
                mock_q.side_effect = fake_query
                result = await match_ingredients(["阿斯巴甜"], mock_session, mock_settings)

        assert len(result["matched"]) == 1
        assert result["matched"][0]["ingredient_id"] == 5
        assert result["unmatched"] == []

    @pytest.mark.asyncio
    async def test_low_similarity_unmatched(self):
        """Above threshold → unmatched."""
        mock_session = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.INGREDIENT_MATCH_THRESHOLD = 0.8

        async def fake_embed(batches, **kw):
            return [[0.9, 0.1]]

        async def fake_query(name, emb, top_k):
            # Distance >= threshold → unmatched
            return [("ingredient_99", 0.95)]

        with patch(
            "workflow_product_analysis.ingredient_matcher.embed_batch", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.side_effect = fake_embed
            with patch(
                "workflow_product_analysis.ingredient_matcher._query_ingredient_collection",
                new_callable=AsyncMock,
            ) as mock_q:
                mock_q.side_effect = fake_query
                result = await match_ingredients(["未知成分X"], mock_session, mock_settings)

        assert result["matched"] == []
        assert result["unmatched"] == ["未知成分X"]

    @pytest.mark.asyncio
    async def test_empty_input(self):
        mock_session = AsyncMock()
        result = await match_ingredients([], mock_session, MagicMock())
        assert result["matched"] == []
        assert result["unmatched"] == []

    @pytest.mark.asyncio
    async def test_collection_missing_falls_back_to_unmatched(self):
        """Collection returns None → unmatched."""
        mock_session = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.INGREDIENT_MATCH_THRESHOLD = 0.8

        async def fake_embed(batches, **kw):
            return [[0.1]]

        async def fake_query(name, emb, top_k):
            return None  # collection 缺失

        with patch(
            "workflow_product_analysis.ingredient_matcher.embed_batch", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.side_effect = fake_embed
            with patch(
                "workflow_product_analysis.ingredient_matcher._query_ingredient_collection",
                new_callable=AsyncMock,
            ) as mock_q:
                mock_q.side_effect = fake_query
                result = await match_ingredients(["糖"], mock_session, mock_settings)

        assert result["unmatched"] == ["糖"]


class TestFetchIngredientDetails:
    @pytest.mark.asyncio
    async def test_returns_name_category_level(self):
        mock_session = AsyncMock()
        mock_ing = MagicMock()
        mock_ing.name = "糖"
        mock_ing.function_type = ["甜味剂", "碳水化合物"]
        mock_analysis = MagicMock()
        mock_analysis.level = "t1"
        mock_result_ing = MagicMock()
        mock_result_ing.scalar_one_or_none.return_value = mock_ing
        mock_result_analysis = MagicMock()
        mock_result_analysis.scalar_one_or_none.return_value = mock_analysis
        mock_session.execute.side_effect = [mock_result_ing, mock_result_analysis]

        name, category, level = await fetch_ingredient_details(3, mock_session)

        assert name == "糖"
        assert category == "甜味剂 · 碳水化合物"
        assert level == "t1"

    @pytest.mark.asyncio
    async def test_no_analysis_unknown_level(self):
        mock_session = AsyncMock()
        mock_ing = MagicMock()
        mock_ing.name = "新成分"
        mock_ing.function_type = []
        mock_result_ing = MagicMock()
        mock_result_ing.scalar_one_or_none.return_value = mock_ing
        mock_result_analysis = MagicMock()
        mock_result_analysis.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [mock_result_ing, mock_result_analysis]

        name, category, level = await fetch_ingredient_details(99, mock_session)

        assert level == "unknown"
