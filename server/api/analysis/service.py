"""Service layer for analysis endpoints."""
from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.models import FeedbackRequest, FeedbackResponse
from config import Settings
from database.models import AnalysisFeedback
from workflow_product_analysis.pipeline import run_analysis_pipeline
from workflow_product_analysis.redis_store import create_task, get_task

if TYPE_CHECKING:
    import redis.asyncio as redis


class TaskNotFoundError(Exception):
    pass


async def start_analysis(
    image_bytes: bytes,
    food_id: int | None,
    background_tasks: BackgroundTasks,
    redis: "redis.Redis",
    session: AsyncSession,
    settings: Settings,
) -> str:
    """
    启动分析任务。

    1. 生成 task_id（uuid4）
    2. create_task(redis, task_id)
    3. background_tasks.add_task(run_analysis_pipeline, ...)
    4. 返回 task_id
    """
    task_id = str(uuid.uuid4())
    await create_task(redis, task_id)
    background_tasks.add_task(
        run_analysis_pipeline,
        task_id=task_id,
        image_bytes=image_bytes,
        explicit_food_id=food_id,
        redis=redis,
        session=session,
        settings=settings,
    )
    return task_id


async def get_task_status(
    task_id: str,
    redis: "redis.Redis",
) -> dict:
    """
    查询任务状态。

    任务不存在 → raise TaskNotFoundError
    """
    task = await get_task(redis, task_id)
    if task is None:
        raise TaskNotFoundError(f"Task {task_id!r} not found")
    return task


async def submit_feedback(
    req: FeedbackRequest,
    request: Request,
    session: AsyncSession,
) -> FeedbackResponse:
    """
    写入用户反馈到 analysis_feedback 表。

    追加字段：source_ip_hash、user_agent
    """
    # IP hash
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
        reporter_user_id=None,  # 未登录用户
        source_ip_hash=ip_hash,
        user_agent=ua,
    )
    session.add(record)
    await session.flush()

    return FeedbackResponse(accepted=True)
