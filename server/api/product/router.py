from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.product.models import ProductResponse
from database.session import get_async_session
from db_repositories.food import FoodRepository

router = APIRouter()


def get_food_repository(session: AsyncSession = Depends(get_async_session)) -> FoodRepository:
    return FoodRepository(session)


@router.get("/product", response_model=ProductResponse, tags=["Product"])
async def get_product_by_barcode(
    barcode: str,
    repo: FoodRepository = Depends(get_food_repository),
):
    """通过条形码查询产品完整信息（营养成分 + 配料 + AI 分析）。"""
    result = await repo.fetch_by_barcode(barcode)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(
        id=result.id,
        barcode=result.barcode,
        name=result.name,
        manufacturer=result.manufacturer,
        origin_place=result.origin_place,
        shelf_life=result.shelf_life,
        net_content=result.net_content,
        image_url_list=result.image_url_list,
        nutritions=[n.__dict__ for n in result.nutritions],
        ingredients=[
            {**i.__dict__, "analysis": i.analysis}
            for i in result.ingredients
        ],
        analysis=[a.__dict__ for a in result.analysis],
    )
