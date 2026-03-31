"""Tests for analysis pipeline orchestrator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_product_analysis.pipeline import run_analysis_pipeline


class TestRunAnalysisPipeline:
    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.ANALYSIS_TASK_TTL_SECONDS = 3600
        s.SYSTEM_USER_ID = "system-uuid"
        s.DEFAULT_MODEL = "MiniMax-2.7"
        return s

    @pytest.mark.asyncio
    async def test_ocr_failure_sets_failed(self, mock_redis, mock_session, mock_settings):
        """OCR 抛出 OcrServiceError → status='failed', error='ocr_failed'。"""
        from workflow_product_analysis.ocr_client import OcrServiceError

        with patch(
            "workflow_product_analysis.pipeline._upload_image_to_storage",
            new_callable=AsyncMock,
        ):
            with patch(
                "workflow_product_analysis.pipeline.run_ocr",
                new_callable=AsyncMock,
            ) as mock_ocr:
                mock_ocr.side_effect = OcrServiceError("network error")

                with patch(
                    "workflow_product_analysis.pipeline.set_task_failed",
                    new_callable=AsyncMock,
                ) as mock_fail:
                    await run_analysis_pipeline(
                        task_id="t1",
                        image_bytes=b"fake",
                        explicit_food_id=None,
                        redis=mock_redis,
                        session=mock_session,
                        settings=mock_settings,
                    )

                mock_fail.assert_called_once()
                call_args = mock_fail.call_args[0]
                assert call_args[1] == "t1"
                assert call_args[2] == "ocr_failed"

    @pytest.mark.asyncio
    async def test_no_ingredients_sets_failed(self, mock_redis, mock_session, mock_settings):
        """parse_ingredients 抛出 NoIngredientsFoundError → error='no_ingredients_found'。"""
        from workflow_product_analysis.ingredient_parser import NoIngredientsFoundError

        with patch(
            "workflow_product_analysis.pipeline._upload_image_to_storage",
            new_callable=AsyncMock,
        ):
            with patch(
                "workflow_product_analysis.pipeline.run_ocr",
                new_callable=AsyncMock,
            ) as mock_ocr:
                mock_ocr.return_value = "无配料"

                with patch(
                    "workflow_product_analysis.pipeline.update_task_status",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "workflow_product_analysis.pipeline.parse_ingredients",
                        new_callable=AsyncMock,
                    ) as mock_parse:
                        mock_parse.side_effect = NoIngredientsFoundError("no ingredients")

                        with patch(
                            "workflow_product_analysis.pipeline.set_task_failed",
                            new_callable=AsyncMock,
                        ) as mock_fail:
                            await run_analysis_pipeline(
                                task_id="t3",
                                image_bytes=b"img",
                                explicit_food_id=None,
                                redis=mock_redis,
                                session=mock_session,
                                settings=mock_settings,
                            )

                        mock_fail.assert_called_once()
                        assert mock_fail.call_args[0][2] == "no_ingredients_found"

    @pytest.mark.asyncio
    async def test_invalid_food_id_sets_failed(self, mock_redis, mock_session, mock_settings):
        """resolve_food_id 抛出 InvalidFoodIdError → error='invalid_food_id'。"""
        from workflow_product_analysis.food_resolver import InvalidFoodIdError

        with patch(
            "workflow_product_analysis.pipeline._upload_image_to_storage",
            new_callable=AsyncMock,
        ):
            with patch(
                "workflow_product_analysis.pipeline.run_ocr",
                new_callable=AsyncMock,
            ) as mock_ocr:
                mock_ocr.return_value = "配料：糖"

                with patch(
                    "workflow_product_analysis.pipeline.update_task_status",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "workflow_product_analysis.pipeline.parse_ingredients",
                        new_callable=AsyncMock,
                    ) as mock_parse:
                        mock_parse.return_value = MagicMock(
                            ingredients=["糖"], product_name="可乐"
                        )

                        with patch(
                            "workflow_product_analysis.pipeline.resolve_food_id",
                            new_callable=AsyncMock,
                        ) as mock_resolve:
                            mock_resolve.side_effect = InvalidFoodIdError("bad id")

                            with patch(
                                "workflow_product_analysis.pipeline.set_task_failed",
                                new_callable=AsyncMock,
                            ) as mock_fail:
                                await run_analysis_pipeline(
                                    task_id="t4",
                                    image_bytes=b"img",
                                    explicit_food_id=999,
                                    redis=mock_redis,
                                    session=mock_session,
                                    settings=mock_settings,
                                )

                            mock_fail.assert_called_once()
                            assert mock_fail.call_args[0][2] == "invalid_food_id"

    @pytest.mark.asyncio
    async def test_db_cache_hit_returns_db_cache(self, mock_redis, mock_session, mock_settings):
        """DB 命中 → source='db_cache'，跳过 Agent。"""
        mock_pa = MagicMock()
        mock_pa.level = "t1"
        mock_pa.description = "desc"
        mock_pa.advice = "advice"
        mock_pa.demographics = []
        mock_pa.scenarios = []
        mock_pa.references = []

        with patch(
            "workflow_product_analysis.pipeline._upload_image_to_storage",
            new_callable=AsyncMock,
        ):
            with patch(
                "workflow_product_analysis.pipeline.run_ocr",
                new_callable=AsyncMock,
            ) as mock_ocr:
                mock_ocr.return_value = "配料：糖"

                with patch(
                    "workflow_product_analysis.pipeline.update_task_status",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "workflow_product_analysis.pipeline.parse_ingredients",
                        new_callable=AsyncMock,
                    ) as mock_parse:
                        mock_parse.return_value = MagicMock(
                            ingredients=["糖"], product_name=None
                        )

                        with patch(
                            "workflow_product_analysis.pipeline.resolve_food_id",
                            new_callable=AsyncMock,
                        ) as mock_resolve:
                            mock_resolve.return_value = 5

                            with patch(
                                "workflow_product_analysis.pipeline.match_ingredients",
                                new_callable=AsyncMock,
                            ) as mock_match:
                                mock_match.return_value = MagicMock(
                                    matched=[MagicMock(ingredient_id=1, name="糖", level="t2")],
                                    unmatched=[],
                                )

                                with patch(
                                    "workflow_product_analysis.pipeline.get_by_food_id",
                                    new_callable=AsyncMock,
                                ) as mock_get:
                                    mock_get.return_value = mock_pa

                                    with patch(
                                        "workflow_product_analysis.pipeline.assemble_from_db_cache",
                                        new_callable=AsyncMock,
                                    ) as mock_assemble:
                                        mock_assemble.return_value = {
                                            "source": "db_cache",
                                            "ingredients": [],
                                            "verdict": {"level": "t1", "description": "desc"},
                                            "advice": "advice",
                                            "alternatives": [],
                                            "demographics": [],
                                            "scenarios": [],
                                            "references": [],
                                        }

                                        with patch(
                                            "workflow_product_analysis.pipeline.set_task_done",
                                            new_callable=AsyncMock,
                                        ) as mock_done:
                                            await run_analysis_pipeline(
                                                task_id="t5",
                                                image_bytes=b"img",
                                                explicit_food_id=None,
                                                redis=mock_redis,
                                                session=mock_session,
                                                settings=mock_settings,
                                            )

                                        mock_done.assert_called_once()
                                        done_result = mock_done.call_args[0][2]
                                        assert done_result["source"] == "db_cache"
                                        # Agent should NOT have been called
                                        mock_parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_failure_sets_analysis_failed(
        self, mock_redis, mock_session, mock_settings
    ):
        """Agent 抛出 ProductAgentError → error='analysis_failed'。"""
        from workflow_product_analysis.product_agent.graph import ProductAgentError

        with patch(
            "workflow_product_analysis.pipeline._upload_image_to_storage",
            new_callable=AsyncMock,
        ):
            with patch(
                "workflow_product_analysis.pipeline.run_ocr",
                new_callable=AsyncMock,
            ) as mock_ocr:
                mock_ocr.return_value = "配料：糖"

                with patch(
                    "workflow_product_analysis.pipeline.update_task_status",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "workflow_product_analysis.pipeline.parse_ingredients",
                        new_callable=AsyncMock,
                    ) as mock_parse:
                        mock_parse.return_value = MagicMock(
                            ingredients=["糖"], product_name=None
                        )

                        with patch(
                            "workflow_product_analysis.pipeline.resolve_food_id",
                            new_callable=AsyncMock,
                        ) as mock_resolve:
                            mock_resolve.return_value = 5

                            with patch(
                                "workflow_product_analysis.pipeline.match_ingredients",
                                new_callable=AsyncMock,
                            ) as mock_match:
                                mock_match.return_value = MagicMock(
                                    matched=[MagicMock(ingredient_id=1, name="糖", level="t2")],
                                    unmatched=[],
                                )

                                with patch(
                                    "workflow_product_analysis.pipeline.get_by_food_id",
                                    new_callable=AsyncMock,
                                ) as mock_get:
                                    mock_get.return_value = None  # 跳过 DB 缓存

                                    with patch(
                                        "workflow_product_analysis.pipeline.run_product_analysis_agent",
                                        new_callable=AsyncMock,
                                    ) as mock_agent:
                                        mock_agent.side_effect = ProductAgentError(
                                            "LLM error"
                                        )

                                        with patch(
                                            "workflow_product_analysis.pipeline.set_task_failed",
                                            new_callable=AsyncMock,
                                        ) as mock_fail:
                                            await run_analysis_pipeline(
                                                task_id="t6",
                                                image_bytes=b"img",
                                                explicit_food_id=None,
                                                redis=mock_redis,
                                                session=mock_session,
                                                settings=mock_settings,
                                            )

                                        mock_fail.assert_called_once()
                                        assert mock_fail.call_args[0][2] == "analysis_failed"

