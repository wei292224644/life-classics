"""FastAPI router for analysis endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.models import (
    AnalysisStatusResponse,
    FeedbackRequest,
    FeedbackResponse,
    StartAnalysisResponse,
)
from api.analysis.service import (
    get_task_status,
    start_analysis,
    submit_feedback,
    TaskNotFoundError,
)
from database.session import get_async_session
from workflow_product_analysis.redis_store import get_redis_client

router = APIRouter()


@router.post(
    "/start",
    response_model=StartAnalysisResponse,
    status_code=201,
    summary="启动产品分析",
)
async def api_start_analysis(
    background_tasks: BackgroundTasks,
    redis: Annotated[Redis, Depends(get_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    image: UploadFile = File(...),
    food_id: int | None = Form(default=None),
) -> StartAnalysisResponse:
    """
    启动产品分析任务。

    - 接受 multipart/form-data（含 image 和可选 food_id）
    - 返回 task_id，前端轮询 status 端点获取进度
    """
    from config import settings as app_settings

    image_bytes = await image.read()
    task_id = await start_analysis(
        image_bytes=image_bytes,
        food_id=food_id,
        background_tasks=background_tasks,
        redis=redis,
        session=session,
        settings=app_settings,
    )
    return StartAnalysisResponse(task_id=task_id)


@router.get(
    "/{task_id}/status",
    response_model=AnalysisStatusResponse,
    summary="查询分析任务状态",
)
async def api_get_status(
    task_id: str,
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> AnalysisStatusResponse:
    """
    查询任务当前状态。

    - status: "ocr" | "parsing" | "analyzing" | "done" | "failed"
    - error: 失败时给出具体原因
    - result: 完成时返回完整分析结果
    - 任务不存在 → HTTP 404
    """
    try:
        task = await get_task_status(task_id, redis)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")

    return AnalysisStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        error=task.get("error"),
        result=task.get("result"),
    )


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="提交分析反馈",
)
async def api_feedback(
    req: FeedbackRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> FeedbackResponse:
    """
    提交用户对分析结果的反馈。

    反馈类型：ocr_wrong | verdict_wrong | ingredient_wrong | other
    """
    return await submit_feedback(req=req, request=request, session=session)
