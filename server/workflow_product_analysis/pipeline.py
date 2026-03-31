"""产品分析管道编排 — 串联四组件，在 BackgroundTask 中执行。"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import structlog

from config import Settings
from db_repositories.product_analysis import get_by_food_id, insert_if_absent
from workflow_product_analysis.assembler import (
    assemble_from_agent_output,
    assemble_from_db_cache,
)
from workflow_product_analysis.food_resolver import (
    InvalidFoodIdError,
    resolve_food_id,
)
from workflow_product_analysis.ingredient_matcher import match_ingredients
from workflow_product_analysis.ingredient_parser import (
    NoIngredientsFoundError,
    parse_ingredients,
)
from workflow_product_analysis.ocr_client import OcrServiceError, run_ocr
from workflow_product_analysis.product_agent.graph import (
    ProductAgentError,
    run_product_analysis_agent,
)
from workflow_product_analysis.redis_store import (
    get_task,
    set_task_done,
    set_task_failed,
    update_task_status,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Pipeline TTL for done/failed states (seconds)
_PIPELINE_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


async def _upload_image_to_storage(
    task_id: str,
    image_bytes: bytes,
    settings: Settings,
) -> None:
    """
    上传图片到对象存储（异步旁路，失败仅记 warning）。

    Key 格式：analysis_uploads/{yyyy}/{mm}/{task_id}.jpg

    MVP 实现为 no-op，待对象存储选型（OSS/S3/MinIO）确定后实现。
    """
    # TODO: 实现真实上传
    logger.warning("image_upload_not_implemented", task_id=task_id)


async def run_analysis_pipeline(
    task_id: str,
    image_bytes: bytes,
    explicit_food_id: int | None,
    redis: "Redis",
    session: "AsyncSession",
    settings: Settings,
) -> None:
    """
    完整产品分析管道，无返回值，通过 Redis 更新状态。

    每步失败均调用 set_task_failed 后 return：
      - OCR 失败 → error="ocr_failed"
      - 成分解析失败 → error="no_ingredients_found"
      - food_id 无效 → error="invalid_food_id"
      - Agent 失败 → error="analysis_failed"
    """
    ttl = settings.ANALYSIS_TASK_TTL_SECONDS or _PIPELINE_TTL_SECONDS

    # [异步旁路] 触发图片上传（不 await，允许失败）
    # 注意：Python 不支持真正 fire-and-forget，这里用 create_task
    import asyncio

    asyncio.create_task(
        _upload_image_to_storage(task_id, image_bytes, settings)
    )

    # ── 步骤 1：OCR ────────────────────────────────────────────────────────
    # Redis 状态已是 "ocr"（create_task 时写入）
    try:
        ocr_text = await run_ocr(image_bytes, settings)
        logger.info("pipeline_ocr_done", task_id=task_id, text_len=len(ocr_text))
    except OcrServiceError:
        logger.error("pipeline_ocr_failed", task_id=task_id)
        await set_task_failed(redis, task_id, "ocr_failed", ttl)
        return

    # ── 步骤 2：解析成分 ────────────────────────────────────────────────────
    await update_task_status(redis, task_id, "parsing")
    try:
        parse_result = await parse_ingredients(ocr_text, settings)
        logger.info(
            "pipeline_parsing_done",
            task_id=task_id,
            ingredient_count=len(parse_result.ingredients),
        )
    except NoIngredientsFoundError:
        logger.error("pipeline_no_ingredients", task_id=task_id)
        await set_task_failed(redis, task_id, "no_ingredients_found", ttl)
        return

    # ── 步骤 3：resolve_food_id ─────────────────────────────────────────────
    try:
        food_id = await resolve_food_id(
            explicit_food_id=explicit_food_id,
            product_name=parse_result.product_name,
            task_id=task_id,
            session=session,
            settings=settings,
        )
        logger.info("pipeline_food_id_resolved", task_id=task_id, food_id=food_id)
    except InvalidFoodIdError:
        logger.error("pipeline_invalid_food_id", task_id=task_id)
        await set_task_failed(redis, task_id, "invalid_food_id", ttl)
        return

    # ── 步骤 4：成分匹配 ────────────────────────────────────────────────────
    await update_task_status(redis, task_id, "analyzing")
    match_result = await match_ingredients(
        parse_result.ingredients, session, settings
    )
    logger.info(
        "pipeline_matching_done",
        task_id=task_id,
        matched=len(match_result.matched),
        unmatched=len(match_result.unmatched),
    )

    # 构建 IngredientInput 列表（unmatched → id=0, level="unknown", safety_info=""）
    from workflow_product_analysis.types import IngredientInput

    ingredient_inputs: list[IngredientInput] = []
    matched_ids: list[int] = []
    for m in match_result.matched:
        ingredient_inputs.append(
            IngredientInput(
                ingredient_id=m["ingredient_id"],
                name=m["name"],
                category="",  # fetch_ingredient_details 已解析，可进一步补全
                level=m["level"],
                safety_info="",
            )
        )
        matched_ids.append(m["ingredient_id"])

    for name in match_result.unmatched:
        ingredient_inputs.append(
            IngredientInput(
                ingredient_id=0,
                name=name,
                category="",
                level="unknown",
                safety_info="",
            )
        )

    # ── 步骤 5：DB 缓存命中检测 ────────────────────────────────────────────
    existing = await get_by_food_id(food_id, session)

    if existing is not None:
        logger.info("pipeline_db_cache_hit", task_id=task_id, food_id=food_id)
        result = await assemble_from_db_cache(
            product_analysis=existing,
            matched_ids=matched_ids,
            session=session,
        )
        await set_task_done(redis, task_id, result, ttl)
        return

    # ── 步骤 6：Agent 生成 + 写库 + 组装 ──────────────────────────────────
    logger.info("pipeline_agent_generating", task_id=task_id, food_id=food_id)

    try:
        agent_output = await run_product_analysis_agent(ingredient_inputs, settings)
    except ProductAgentError:
        logger.error("pipeline_agent_failed", task_id=task_id)
        await set_task_failed(redis, task_id, "analysis_failed", ttl)
        return

    # 写入 product_analyses（insert_if_absent）
    agent_output["unmatched_ingredient_names"] = match_result.unmatched
    analysis_data = {
        "ai_model": settings.DEFAULT_MODEL,
        "level": agent_output.get("verdict_level", "t3"),
        "description": agent_output.get("verdict_description", ""),
        "advice": agent_output.get("advice", ""),
        "demographics": agent_output.get("demographics", []),
        "scenarios": agent_output.get("scenarios", []),
        "references": agent_output.get("references", []),
    }
    await insert_if_absent(
        food_id=food_id,
        data=analysis_data,
        created_by_user=settings.SYSTEM_USER_ID,
        session=session,
    )

    result = await assemble_from_agent_output(
        agent_output=agent_output,
        matched_ids=matched_ids,
        session=session,
    )

    # ── 完成 ────────────────────────────────────────────────────────────────
    await set_task_done(redis, task_id, result, ttl)
    logger.info("pipeline_done", task_id=task_id, source=result["source"])
