"""Tests for result assembler."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from workflow_product_analysis.assembler import (
    assemble_from_agent_output,
    assemble_from_db_cache,
)


class TestAssembleFromDbCache:
    @pytest.mark.asyncio
    async def test_source_db_cache(self):
        """source 字段为 'db_cache'。"""
        mock_pa = MagicMock()
        mock_pa.level = "t2"
        mock_pa.description = "含甜味剂"
        mock_pa.advice = "少喝"
        mock_pa.demographics = []
        mock_pa.scenarios = []
        mock_pa.references = []

        mock_session = AsyncMock()

        result = await assemble_from_db_cache(
            mock_pa, matched_ids=[], session=mock_session
        )

        assert result["source"] == "db_cache"
        assert result["verdict"]["level"] == "t2"


class TestAssembleFromAgentOutput:
    @pytest.mark.asyncio
    async def test_source_agent_generated(self):
        """source 字段为 'agent_generated'。"""
        mock_session = AsyncMock()
        # No ingredients matched
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [mock_result, mock_result2]

        agent_output = {
            "verdict_level": "t1",
            "verdict_description": "整体安全",
            "advice": "适量饮用",
            "demographics": [],
            "scenarios": [],
            "references": ["GB 2760"],
            "unmatched_ingredient_names": ["神秘添加物"],
        }

        result = await assemble_from_agent_output(
            agent_output, matched_ids=[], session=mock_session
        )

        assert result["source"] == "agent_generated"
        assert result["verdict"]["level"] == "t1"
        assert result["advice"] == "适量饮用"
        # unmatched 成分 → unknown 条目
        assert any(
            item["level"] == "unknown" and item["name"] == "神秘添加物"
            for item in result["ingredients"]
        )
