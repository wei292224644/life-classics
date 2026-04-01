from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.product.models import ProductResponse
from api.product.service import ProductService
from database.session import get_async_session
from db_repositories.food import FoodRepository


router = APIRouter(prefix="/products")


def get_food_repository(session: AsyncSession = Depends(get_async_session)) -> FoodRepository:
    return FoodRepository(session)


def get_product_service(food_repo: FoodRepository = Depends(get_food_repository)) -> ProductService:
    return ProductService(food_repo)


@router.get("/{food_id}", response_model=ProductResponse, tags=["Product"])
async def get_product_by_id(
    food_id: int,
    svc: ProductService = Depends(get_product_service),
):
    """通过产品 ID 查询产品完整信息（营养成分 + 配料）。"""
    try:
        return await svc.get_product_by_id(food_id)
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status_code=404, detail="Product not found")
        raise
