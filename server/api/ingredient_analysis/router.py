"""Router for ingredient_analysis API — DB writes only."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.ingredient_analysis.models import (
    IngredientAnalysisCreate,
    IngredientAnalysisResponse,
)
from api.ingredient_analysis.service import IngredientAnalysisService
from database.session import get_async_session

router = APIRouter(prefix="/ingredient-analyses", tags=["IngredientAnalysis"])


def get_service(
    session: AsyncSession = Depends(get_async_session),
) -> IngredientAnalysisService:
    return IngredientAnalysisService(session)


@router.post(
    "/{ingredient_id}",
    response_model=IngredientAnalysisResponse,
    status_code=201,
)
async def create_ingredient_analysis(
    ingredient_id: int,
    body: IngredientAnalysisCreate,
    svc: IngredientAnalysisService = Depends(get_service),
):
    """写入配料分析结果（供调用方在 workflow 结束后调用）。"""
    return await svc.create(ingredient_id, body.model_dump())