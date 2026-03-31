"""E2E smoke tests for the full analysis pipeline."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_product_analysis.pipeline import run_analysis_pipeline


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.ANALYSIS_TASK_TTL_SECONDS = 3600
    s.SYSTEM_USER_ID = "system-uuid"
    s.DEFAULT_MODEL = "MiniMax-2.7"
    return s


class TestPipelineSmoke:
    @pytest.mark.asyncio
    async def test_pipeline_smoke_cached_food_id(self, mock_redis, mock_session, mock_settings):
        """
        场景：food_id 已有 product_analyses 记录
        Mock: OCR 返回固定文本、parse 返回固定列表
              DB 中预置 ProductAnalysis 记录
        验证：最终 Redis 状态为 done，result.source = "db_cache"
        """
        mock_pa = MagicMock()
        mock_pa.level = "t2"
        mock_pa.description = "含人工甜味剂"
        mock_pa.advice = "不宜过多"
        mock_pa.demographics = []
        mock_pa.scenarios = []
        mock_pa.references = []

        MockRepo = MagicMock()
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_food_id = AsyncMock(return_value=mock_pa)
        mock_repo_instance.insert_if_absent = AsyncMock()
        MockRepo.return_value = mock_repo_instance

        with patch(
            "workflow_product_analysis.pipeline._upload_image_to_storage",
            new_callable=AsyncMock,
        ):
            with patch(
                "workflow_product_analysis.pipeline.run_ocr",
                new_callable=AsyncMock,
            ) as mock_ocr:
                mock_ocr.return_value = "配料：糖、阿斯巴甜、山梨酸钾"

                with patch(
                    "workflow_product_analysis.pipeline.update_task_status",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "workflow_product_analysis.pipeline.parse_ingredients",
                        new_callable=AsyncMock,
                    ) as mock_parse:
                        mock_parse.return_value = MagicMock(
                            ingredients=["糖", "阿斯巴甜", "山梨酸钾"],
                            product_name="某饮料",
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
                                    matched=[
                                        MagicMock(
                                            ingredient_id=1, name="糖", level="t2"
                                        ),
                                        MagicMock(
                                            ingredient_id=2,
                                            name="阿斯巴甜",
                                            level="t2",
                                        ),
                                    ],
                                    unmatched=["山梨酸钾"],
                                )

                                with patch(
                                    "workflow_product_analysis.pipeline.ProductAnalysisRepository",
                                    MockRepo,
                                ):
                                    with patch(
                                        "workflow_product_analysis.pipeline.assemble_from_db_cache",
                                        new_callable=AsyncMock,
                                    ) as mock_assemble:
                                        mock_assemble.return_value = {
                                            "source": "db_cache",
                                            "ingredients": [],
                                            "verdict": {
                                                "level": "t2",
                                                "description": "含人工甜味剂",
                                            },
                                            "advice": "不宜过多",
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
                                                task_id="smoke-t1",
                                                image_bytes=b"fake",
                                                explicit_food_id=None,
                                                redis=mock_redis,
                                                session=mock_session,
                                                settings=mock_settings,
                                            )

                                        mock_done.assert_called_once()
                                        done_result = mock_done.call_args[0][2]
                                        assert (
                                            done_result["source"] == "db_cache"
                                        )

    @pytest.mark.asyncio
    async def test_pipeline_smoke_agent_generated(self, mock_redis, mock_session, mock_settings):
        """
        场景：food_id 无 product_analyses 记录
        Mock: 所有 LLM 调用返回固定结构
              DB 中预置 IngredientAnalysis 记录
        验证：最终 Redis 状态为 done，result.source = "agent_generated"
        """
        MockRepo = MagicMock()
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_food_id = AsyncMock(return_value=None)
        mock_repo_instance.insert_if_absent = AsyncMock()
        MockRepo.return_value = mock_repo_instance

        with patch(
            "workflow_product_analysis.pipeline._upload_image_to_storage",
            new_callable=AsyncMock,
        ):
            with patch(
                "workflow_product_analysis.pipeline.run_ocr",
                new_callable=AsyncMock,
            ) as mock_ocr:
                mock_ocr.return_value = "配料：燕麦粉、麦芽糊精"

                with patch(
                    "workflow_product_analysis.pipeline.update_task_status",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "workflow_product_analysis.pipeline.parse_ingredients",
                        new_callable=AsyncMock,
                    ) as mock_parse:
                        mock_parse.return_value = MagicMock(
                            ingredients=["燕麦粉", "麦芽糊精"],
                            product_name=None,
                        )

                        with patch(
                            "workflow_product_analysis.pipeline.resolve_food_id",
                            new_callable=AsyncMock,
                        ) as mock_resolve:
                            mock_resolve.return_value = 7

                            with patch(
                                "workflow_product_analysis.pipeline.match_ingredients",
                                new_callable=AsyncMock,
                            ) as mock_match:
                                mock_match.return_value = MagicMock(
                                    matched=[MagicMock(ingredient_id=10, name="燕麦粉", level="t0")],
                                    unmatched=["麦芽糊精"],
                                )

                                with patch(
                                    "workflow_product_analysis.pipeline.ProductAnalysisRepository",
                                    MockRepo,
                                ):
                                    with patch(
                                        "workflow_product_analysis.pipeline.run_product_analysis_agent",
                                        new_callable=AsyncMock,
                                    ) as mock_agent:
                                        mock_agent.return_value = {
                                            "demographics": [],
                                            "scenarios": [],
                                            "advice": "适量食用",
                                            "verdict_level": "t1",
                                            "verdict_description": "相对安全",
                                            "references": ["GB 2760"],
                                            "unmatched_ingredient_names": ["麦芽糊精"],
                                        }

                                        with patch(
                                            "workflow_product_analysis.pipeline.assemble_from_agent_output",
                                            new_callable=AsyncMock,
                                        ) as mock_assemble:
                                            mock_assemble.return_value = {
                                                "source": "agent_generated",
                                                "ingredients": [],
                                                "verdict": {
                                                    "level": "t1",
                                                    "description": "相对安全",
                                                },
                                                "advice": "适量食用",
                                                "alternatives": [],
                                                "demographics": [],
                                                "scenarios": [],
                                                "references": ["GB 2760"],
                                            }

                                            with patch(
                                                "workflow_product_analysis.pipeline.set_task_done",
                                                new_callable=AsyncMock,
                                            ) as mock_done:
                                                await run_analysis_pipeline(
                                                    task_id="smoke-t2",
                                                    image_bytes=b"fake",
                                                    explicit_food_id=None,
                                                    redis=mock_redis,
                                                    session=mock_session,
                                                    settings=mock_settings,
                                                )

                                            mock_done.assert_called_once()
                                            done_result = mock_done.call_args[0][2]
                                            assert (
                                                done_result["source"]
                                                == "agent_generated"
                                            )

    @pytest.mark.asyncio
    async def test_pipeline_smoke_ocr_failure(self, mock_redis, mock_session, mock_settings):
        """
        Mock: OCR 服务抛出 OcrServiceError
        验证：Redis 状态为 failed, error="ocr_failed"
        """
        from workflow_product_analysis.ocr_client import OcrServiceError

        with patch(
            "workflow_product_analysis.pipeline._upload_image_to_storage",
            new_callable=AsyncMock,
        ):
            with patch(
                "workflow_product_analysis.pipeline.run_ocr",
                new_callable=AsyncMock,
            ) as mock_ocr:
                mock_ocr.side_effect = OcrServiceError("connection refused")

                with patch(
                    "workflow_product_analysis.pipeline.set_task_failed",
                    new_callable=AsyncMock,
                ) as mock_fail:
                    await run_analysis_pipeline(
                        task_id="smoke-t3",
                        image_bytes=b"fake",
                        explicit_food_id=None,
                        redis=mock_redis,
                        session=mock_session,
                        settings=mock_settings,
                    )

                mock_fail.assert_called_once()
                assert mock_fail.call_args[0][2] == "ocr_failed"
