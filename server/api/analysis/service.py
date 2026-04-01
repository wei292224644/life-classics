"""Analysis orchestration service — coordinates OCR, parsing, DB ops, and LLM agent."""
from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.assembler import assemble_from_agent_output, assemble_from_db_cache
from api.analysis.food_resolver import InvalidFoodIdError, resolve_food_id
from api.analysis.ingredient_matcher import fetch_ingredient_details, match_ingredients
from api.analysis.ingredient_parser import NoIngredientsFoundError, parse_ingredients
from api.analysis.models import FeedbackRequest, FeedbackResponse
from api.analysis.ocr_client import run_ocr
from config import Settings
from database.models import AnalysisFeedback
from db_repositories.product_analysis import ProductAnalysisRepository
from workflow_product_analysis.product_agent.graph import (
    ProductAgentError,
    build_product_analysis_graph,
)
from workflow_product_analysis.product_agent.types import ProductAnalysisState
from workflow_product_analysis.types import IngredientInput


class AnalysisError(Exception):
    """通用分析错误（不区分具体类型，供 router 捕获转换为 HTTP 状态码）。"""

    def __init__(self, message: str, http_status: int = 500):
        super().__init__(message)
        self.http_status = http_status


class TaskNotFoundError(Exception):
    """保留供后续 SSE 端点使用。"""
    pass


async def start_analysis(
    image_bytes: bytes,
    food_id: int | None,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    settings: Settings,
) -> str:
    """
    启动异步分析任务，立即返回 task_id。
    实际分析在后台 BackgroundTasks 中执行。
    """
    task_id = str(uuid.uuid4())
    background_tasks.add_task(
        run_analysis_in_background,
        task_id=task_id,
        image_bytes=image_bytes,
        explicit_food_id=food_id,
        session=session,
        settings=settings,
    )
    return task_id


async def run_analysis_in_background(
    task_id: str,
    image_bytes: bytes,
    explicit_food_id: int | None,
    session: AsyncSession,
    settings: Settings,
) -> None:
    """
    后台分析管道（由 BackgroundTasks 调用）。
    不返回结果，结果写入 Redis 后由 SSE/轮询端点推送。
    """
    try:
        await run_analysis_sync(
            image_bytes=image_bytes,
            explicit_food_id=explicit_food_id,
            session=session,
            settings=settings,
        )
    except Exception:
        # TODO: 错误处理写入 Redis（后续 SSE 改造时统一处理）
        pass


async def run_analysis_sync(
    image_bytes: bytes,
    explicit_food_id: int | None,
    session: AsyncSession,
    settings: Settings,
) -> dict:
    """
    同步分析管道（可直接调用，跳过 BackgroundTasks）。
    返回完整 ProductAnalysisResult。
    """
    # ① OCR
    ocr_text = await run_ocr(image_bytes, settings)

    # ② 解析成分
    try:
        parse_result = await parse_ingredients(ocr_text, settings)
    except NoIngredientsFoundError:
        raise AnalysisError("无法从图片中提取到配料表", http_status=422)

    # ③ resolve_food_id
    try:
        resolved_food_id = await resolve_food_id(
            explicit_food_id=explicit_food_id,
            product_name=parse_result.product_name,
            task_id=str(uuid.uuid4()),
            session=session,
            settings=settings,
        )
    except InvalidFoodIdError:
        raise AnalysisError("food_id 无效或不存在", http_status=400)

    # ④ 成分匹配
    match_result = await match_ingredients(parse_result.ingredients, session)

    # ⑤ 构建 ingredient_inputs（含 level、safety_info）
    ingredient_inputs: list[IngredientInput] = []
    matched_ids: list[int] = []
    for m in match_result.matched:
        details = await fetch_ingredient_details(m["ingredient_id"], session)
        if details is None:
            continue
        name_db, category_str, level = details
        ingredient_inputs.append(
            IngredientInput(
                ingredient_id=m["ingredient_id"],
                name=name_db,
                category=category_str,
                level=level,
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

    # ⑥ 查 ProductAnalysis 缓存
    product_analysis_repo = ProductAnalysisRepository(session)
    existing = await product_analysis_repo.get_by_food_id(resolved_food_id)
    if existing is not None:
        return await assemble_from_db_cache(
            product_analysis=existing,
            matched_ids=matched_ids,
            session=session,
        )

    # ⑦ Agent 分析
    try:
        graph = build_product_analysis_graph()
        initial_state = ProductAnalysisState(
            ingredients=ingredient_inputs,
            demographics=None,
            scenarios=None,
            advice=None,
            verdict_level=None,
            verdict_description=None,
            references=None,
        )
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        raise ProductAgentError(f"Agent failed: {exc}") from exc

    # ⑧ 组装 + 写缓存
    result = await assemble_from_agent_output(
        agent_output={
            "verdict_level": final_state.get("verdict_level"),
            "verdict_description": final_state.get("verdict_description"),
            "advice": final_state.get("advice"),
            "demographics": final_state.get("demographics", []),
            "scenarios": final_state.get("scenarios", []),
            "references": final_state.get("references", []),
            "unmatched_ingredient_names": match_result.unmatched,
        },
        matched_ids=matched_ids,
        session=session,
    )

    await product_analysis_repo.insert_if_absent(
        food_id=resolved_food_id,
        data={
            "ai_model": settings.DEFAULT_MODEL,
            "level": final_state.get("verdict_level", "t3"),
            "description": final_state.get("verdict_description", ""),
            "advice": final_state.get("advice", ""),
            "demographics": final_state.get("demographics", []),
            "scenarios": final_state.get("scenarios", []),
            "references": final_state.get("references", []),
        },
        created_by_user=settings.SYSTEM_USER_ID,
    )

    return result


async def submit_feedback(
    req: FeedbackRequest,
    request: Request,
    session: AsyncSession,
) -> FeedbackResponse:
    client_ip = request.client.host if request.client else ""
    ip_hash = (
        hashlib.sha256(client_ip.encode()).hexdigest()
        if client_ip
        else None
    )

    ua = request.headers.get("user-agent", "")[:512]

    record = AnalysisFeedback(
        task_id=req.task_id,
        food_id=req.food_id,
        category=req.category,
        message=req.message,
        client_context=req.client_context,
        reporter_user_id=None,
        source_ip_hash=ip_hash,
        user_agent=ua,
    )
    session.add(record)
    await session.flush()

    return FeedbackResponse(accepted=True)
