from enums import RiskLevel
from api.product.models import (
    ProductIngredient,
    ProductIngredientAnalysis,
    ProductResponse,
)
from db_repositories.food import FoodDetail, FoodRepository, ProductIngredientDetail


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
                    "value": n.value,
                    "value_unit": n.value_unit,
                    "reference_unit": n.reference_unit,
                }
                for n in d.nutritions
            ],
            ingredients=[self._to_product_ingredient(i) for i in d.ingredients],
            analysis=[
                {
                    "analysis_type": a.analysis_type,
                    "result": a.result,
                    "source": a.source,
                    "level": a.level,
                    "confidence_score": a.confidence_score,
                }
                for a in d.analysis
            ],
        )

    def _to_product_ingredient(self, i: ProductIngredientDetail) -> ProductIngredient:
        if i.analysis:
            return ProductIngredient(
                id=i.id,
                name=i.name,
                level=RiskLevel.from_str(i.analysis.level),
                reason=i.analysis.reason,
            )
        return ProductIngredient(id=i.id, name=i.name, level=RiskLevel.UNKNOWN, reason=None)
