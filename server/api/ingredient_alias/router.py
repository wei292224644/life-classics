"""API router for ingredient_alias."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.ingredient_alias.models import (
    AliasCreateRequest,
    AliasListResponse,
    AliasResponse,
)
from api.ingredient_alias.service import IngredientAliasService
from database.session import get_async_session


router = APIRouter()


def get_service(session: AsyncSession = Depends(get_async_session)) -> IngredientAliasService:
    return IngredientAliasService(session)


@router.post("", response_model=AliasResponse, tags=["Ingredient Alias"])
async def create_alias(
    req: AliasCreateRequest,
    svc: IngredientAliasService = Depends(get_service),
):
    """创建新别名."""
    try:
        return await svc.create_alias(
            ingredient_id=req.ingredient_id,
            alias=req.alias,
            alias_type=req.alias_type,
        )
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Alias already exists")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{alias_id}", response_model=AliasResponse, tags=["Ingredient Alias"])
async def get_alias(
    alias_id: int,
    svc: IngredientAliasService = Depends(get_service),
):
    """通过 ID 获取别名."""
    alias = await svc.get_alias_by_id(alias_id)
    if alias is None:
        raise HTTPException(status_code=404, detail="Alias not found")
    return alias


@router.get("", response_model=AliasListResponse, tags=["Ingredient Alias"])
async def list_aliases(
    ingredient_id: int | None = None,
    svc: IngredientAliasService = Depends(get_service),
):
    """列出别名，可按配料 ID 筛选."""
    aliases = await svc.list_aliases(ingredient_id=ingredient_id)
    return AliasListResponse(items=aliases, total=len(aliases))


@router.delete("/{alias_id}", tags=["Ingredient Alias"])
async def delete_alias(
    alias_id: int,
    svc: IngredientAliasService = Depends(get_service),
):
    """删除别名."""
    deleted = await svc.delete_alias(alias_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alias not found")
    return {"ok": True}
