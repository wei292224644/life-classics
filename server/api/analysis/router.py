"""FastAPI router for analysis endpoints — L1 层，仅做 HTTP 输入输出和依赖组装。"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.models import (
    FeedbackRequest,
    FeedbackResponse,
    StartAnalysisResponse,
)
from database.session import get_async_session
from db_repositories.food import FoodRepository
from db_repositories.ingredient import IngredientRepository
from db_repositories.ingredient_alias import IngredientAliasRepository
from db_repositories.ingredient_analysis import IngredientAnalysisRepository
from db_repositories.product_analysis import ProductAnalysisRepository
from services.analysis_service import AnalysisService, AnalysisError
from services.product_analysis_service import ProductAnalysisService


# ── 依赖注入工厂 ─────────────────────────────────────────────────────────────

async def get_food_repo(session: Annotated[AsyncSession, Depends(get_async_session)]) -> FoodRepository:
    return FoodRepository(session)


async def get_ingredient_alias_repo(session: Annotated[AsyncSession, Depends(get_async_session)]) -> IngredientAliasRepository:
    return IngredientAliasRepository(session)


async def get_ingredient_repo(session: Annotated[AsyncSession, Depends(get_async_session)]) -> IngredientRepository:
    return IngredientRepository(session)


async def get_ingredient_analysis_repo(session: Annotated[AsyncSession, Depends(get_async_session)]) -> IngredientAnalysisRepository:
    return IngredientAnalysisRepository(session)


async def get_product_analysis_repo(session: Annotated[AsyncSession, Depends(get_async_session)]) -> ProductAnalysisRepository:
    return ProductAnalysisRepository(session)


def get_product_analysis_svc() -> ProductAnalysisService:
    return ProductAnalysisService()


async def get_analysis_service(
    food_repo: Annotated[FoodRepository, Depends(get_food_repo)],
    ingredient_alias_repo: Annotated[IngredientAliasRepository, Depends(get_ingredient_alias_repo)],
    ingredient_repo: Annotated[IngredientRepository, Depends(get_ingredient_repo)],
    ingredient_analysis_repo: Annotated[IngredientAnalysisRepository, Depends(get_ingredient_analysis_repo)],
    product_analysis_repo: Annotated[ProductAnalysisRepository, Depends(get_product_analysis_repo)],
    product_analysis_svc: Annotated[ProductAnalysisService, Depends(get_product_analysis_svc)],
) -> AnalysisService:
    return AnalysisService(
        food_repo=food_repo,
        ingredient_alias_repo=ingredient_alias_repo,
        ingredient_repo=ingredient_repo,
        ingredient_analysis_repo=ingredient_analysis_repo,
        product_analysis_repo=product_analysis_repo,
        product_analysis_svc=product_analysis_svc,
    )


router = APIRouter()


# ── 背景任务入口（L1 保留，由 BackgroundTasks 调用）─────────────────────────────

async def _run_analysis_in_background(
    task_id: str,
    image_bytes: bytes,
    explicit_food_id: int | None,
    session: AsyncSession,
) -> None:
    """后台分析管道（由 BackgroundTasks 调用），结果写入 Redis 后由 SSE/轮询端点推送。"""
    from config import settings as app_settings

    svc = AnalysisService(
        food_repo=FoodRepository(session),
        ingredient_alias_repo=IngredientAliasRepository(session),
        ingredient_repo=IngredientRepository(session),
        ingredient_analysis_repo=IngredientAnalysisRepository(session),
        product_analysis_repo=ProductAnalysisRepository(session),
        product_analysis_svc=ProductAnalysisService(),
    )
    try:
        await svc.run_analysis_sync(
            session=session,
            image_bytes=image_bytes,
            explicit_food_id=explicit_food_id,
            settings=app_settings,
        )
    except Exception:
        # TODO: 错误处理写入 Redis（后续 SSE 改造时统一处理）
        pass


# ── HTTP 端点 ─────────────────────────────────────────────────────────────────

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
    image_bytes = await image.read()
    task_id = str(uuid.uuid4())
    background_tasks.add_task(
        _run_analysis_in_background,
        task_id=task_id,
        image_bytes=image_bytes,
        explicit_food_id=food_id,
        session=session,
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
    client_ip = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")[:512]

    svc = AnalysisService(
        food_repo=FoodRepository(session),
        ingredient_alias_repo=IngredientAliasRepository(session),
        ingredient_repo=IngredientRepository(session),
        ingredient_analysis_repo=IngredientAnalysisRepository(session),
        product_analysis_repo=ProductAnalysisRepository(session),
        product_analysis_svc=ProductAnalysisService(),
    )
    return await svc.submit_feedback(
        session=session,
        req=req,
        client_ip=client_ip,
        user_agent=user_agent,
    )
