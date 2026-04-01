"""FastAPI router for analysis endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.models import (
    FeedbackRequest,
    FeedbackResponse,
    StartAnalysisResponse,
)
from api.analysis.service import (
    start_analysis,
    submit_feedback,
)
from database.session import get_async_session

router = APIRouter()


@router.post(
    "/start",
    response_model=StartAnalysisResponse,
    status_code=201,
    summary="启动产品分析",
)
async def api_start_analysis(
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    image: UploadFile = File(...),
    food_id: int | None = Form(default=None),
) -> StartAnalysisResponse:
    """
    启动产品分析任务。

    - 接受 multipart/form-data（含 image 和可选 food_id）
    - 返回 task_id，结果通过 SSE/轮询端点获取（后续实现）
    """
    from config import settings as app_settings

    image_bytes = await image.read()
    task_id = await start_analysis(
        image_bytes=image_bytes,
        food_id=food_id,
        background_tasks=background_tasks,
        session=session,
        settings=app_settings,
    )
    return StartAnalysisResponse(task_id=task_id)


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
