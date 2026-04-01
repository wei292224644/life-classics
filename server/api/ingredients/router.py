from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import Optional

from api.ingredients.models import IngredientCreate, IngredientUpdate, IngredientPatch
from api.ingredients.models import IngredientsListResponse, IngredientResponse
from database.session import get_async_session
from db_repositories.ingredient import IngredientRepository
from db_repositories.ingredient_analysis import IngredientAnalysisRepository
from api.ingredients.service import IngredientService


router = APIRouter(tags=["Ingredient"])


def get_repo(session=Depends(get_async_session)):
    return IngredientRepository(session)


def get_analysis_repo(session=Depends(get_async_session)):
    return IngredientAnalysisRepository(session)


def get_service(
    repo: IngredientRepository = Depends(get_repo),
    analysis_repo: IngredientAnalysisRepository = Depends(get_analysis_repo),
) -> IngredientService:
    return IngredientService(repo, analysis_repo)


@router.post("", response_model=IngredientResponse, status_code=201)
async def create_ingredient(
    body: IngredientCreate,
    svc: IngredientService = Depends(get_service),
):
    """创建配料（Upsert）。存在则字段级合并."""
    return await svc.create(body)


@router.get("", response_model=IngredientsListResponse)
async def list_ingredients(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    name: Optional[str] = Query(None),
    is_additive: Optional[bool] = Query(None),
    svc: IngredientService = Depends(get_service),
):
    """配料列表查询（分页 + 过滤）."""
    items, total = await svc.list_(limit=limit, offset=offset, name=name, is_additive=is_additive)
    return IngredientsListResponse(items=items, total=total, limit=limit, offset=offset, has_more=offset + len(items) < total)


@router.get("/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: int,
    svc: IngredientService = Depends(get_service),
):
    """获取单个配料详情."""
    result = await svc.get_by_id(ingredient_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result


@router.put("/{ingredient_id}", response_model=IngredientResponse)
async def update_ingredient_full(
    ingredient_id: int,
    body: IngredientUpdate,
    svc: IngredientService = Depends(get_service),
):
    """全量更新配料."""
    result = await svc.update_full(ingredient_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result


@router.patch("/{ingredient_id}", response_model=IngredientResponse)
async def update_ingredient_partial(
    ingredient_id: int,
    body: IngredientPatch,
    svc: IngredientService = Depends(get_service),
):
    """部分更新配料（只更新提供的字段）."""
    result = await svc.update_partial(ingredient_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result


@router.delete("/{ingredient_id}", status_code=204)
async def delete_ingredient(
    ingredient_id: int,
    svc: IngredientService = Depends(get_service),
):
    """软删除配料（幂等）."""
    await svc.delete(ingredient_id)
    return None


@router.post("/{ingredient_id}/analyze", status_code=202)
async def trigger_ingredient_analysis(
    ingredient_id: int,
    background_tasks: BackgroundTasks,
    svc: IngredientService = Depends(get_service),
):
    """
    触发配料分析（异步）。

    编排逻辑：
    1. 查配料数据
    2. 调用 workflow（纯计算）
    3. 写分析结果

    返回 task_id，状态通过 GET /api/analysis/{task_id}/status 查询（若调用方写入了 Redis）。
    """
    result = await svc.trigger_analysis(ingredient_id, background_tasks)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result
