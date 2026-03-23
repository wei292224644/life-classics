from fastapi import HTTPException

from api.product.models import (
    IngredientResponse,
    ProductIngredient,
    ProductIngredientAnalysis,
    ProductResponse,
)
from db_repositories.food import FoodDetail, FoodRepository, ProductIngredientDetail
from db_repositories.ingredient import IngredientDetail, IngredientRepository


class ProductService:
    def __init__(self, food_repo: FoodRepository):
        self._food_repo = food_repo

    async def get_product_by_barcode(self, barcode: str) -> ProductResponse:
        """通过条形码查询产品信息。查不到时由 Router 抛 404。"""
        detail = await self._food_repo.fetch_by_barcode(barcode)
        if detail is None:
            raise ValueError("not_found")
        return self._to_product_response(detail)

    def _to_product_response(self, d: FoodDetail) -> ProductResponse:
        return ProductResponse(
            id=d.id,
            barcode=d.barcode,
            name=d.name,
            manufacturer=d.manufacturer,
            origin_place=d.origin_place,
            shelf_life=d.shelf_life,
            net_content=d.net_content,
            image_url_list=d.image_url_list,
            nutritions=[
                {
                    "name": n.name,
                    "alias": n.alias,
                    "value": n.value,
                    "value_unit": n.value_unit,
                    "reference_type": n.reference_type,
                    "reference_unit": n.reference_unit,
                }
                for n in d.nutritions
            ],
            ingredients=[self._to_product_ingredient(i) for i in d.ingredients],
            analysis=[
                {
                    "id": a.id,
                    "analysis_type": a.analysis_type,
                    "results": a.results,
                    "level": a.level,
                }
                for a in d.analysis
            ],
        )

    def _to_product_ingredient(self, i: ProductIngredientDetail) -> ProductIngredient:
        if i.analysis:
            analysis = ProductIngredientAnalysis(level=i.analysis.level, reason=i.analysis.reason)
        else:
            analysis = None
        return ProductIngredient(
            id=i.id,
            name=i.name,
            who_level=i.who_level,
            function_type=i.function_type,
            allergen_info=i.allergen_info,
            analysis=analysis,
        )


class IngredientService:
    def __init__(self, ingredient_repo: IngredientRepository):
        self._ingredient_repo = ingredient_repo

    async def get_ingredient_by_id(self, ingredient_id: int) -> IngredientResponse:
        """通过配料 ID 查询配料详情。查不到时由 Router 抛 404。"""
        detail = await self._ingredient_repo.fetch_by_id(ingredient_id)
        if detail is None:
            raise ValueError("not_found")
        return self._to_ingredient_response(detail)

    def _to_ingredient_response(self, d: IngredientDetail) -> IngredientResponse:
        # d.analysis 已经是 dict | None 格式（IngredientRepository 返回时已转换）
        analysis_data = None
        if d.analysis:
            analysis_data = {
                "id": d.analysis["id"],
                "analysis_type": d.analysis["analysis_type"],
                "results": d.analysis["results"],
                "level": d.analysis["level"],
            }
        return IngredientResponse(
            id=d.id,
            name=d.name,
            alias=d.alias,
            is_additive=d.is_additive,
            additive_code=d.additive_code,
            who_level=d.who_level,
            allergen_info=d.allergen_info,
            function_type=d.function_type,
            standard_code=d.standard_code,
            analysis=analysis_data,
        )
