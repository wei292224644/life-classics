from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.product.models import IngredientResponse, ProductResponse
from api.product.service import IngredientService, ProductService
from database.session import get_async_session
from db_repositories.food import FoodRepository
from db_repositories.ingredient import IngredientRepository


router = APIRouter()


def get_food_repository(session: AsyncSession = Depends(get_async_session)) -> FoodRepository:
    return FoodRepository(session)


def get_product_service(food_repo: FoodRepository = Depends(get_food_repository)) -> ProductService:
    return ProductService(food_repo)


def get_ingredient_repository(session: AsyncSession = Depends(get_async_session)) -> IngredientRepository:
    return IngredientRepository(session)


def get_ingredient_service(ingredient_repo: IngredientRepository = Depends(get_ingredient_repository)) -> IngredientService:
    return IngredientService(ingredient_repo)


@router.get("/product", response_model=ProductResponse, tags=["Product"])
async def get_product_by_barcode(
    barcode: str,
    svc: ProductService = Depends(get_product_service),
):
    """通过条形码查询产品完整信息（营养成分 + 配料 + AI 分析）。"""
    try:
        return await svc.get_product_by_barcode(barcode)
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status_code=404, detail="Product not found")
        raise


@router.get("/ingredient/{ingredient_id}", response_model=IngredientResponse, tags=["Ingredient"])
async def get_ingredient_by_id(
    ingredient_id: int,
    svc: IngredientService = Depends(get_ingredient_service),
):
    """通过配料 ID 查询配料详情（支持从搜索/对话等独立入口访问）。"""
    try:
        return await svc.get_ingredient_by_id(ingredient_id)
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status_code=404, detail="Ingredient not found")
        raise
