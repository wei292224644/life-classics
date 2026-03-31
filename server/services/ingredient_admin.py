from api.ingredients.models import IngredientCreate, IngredientUpdate, IngredientPatch
from api.product.models import IngredientResponse
from db_repositories.ingredient_admin import IngredientAdminRepository


class IngredientAdminService:
    def __init__(self, repo: IngredientAdminRepository):
        self._repo = repo

    def _to_response(self, ingredient) -> IngredientResponse:
        return IngredientResponse(
            id=ingredient.id,
            name=ingredient.name,
            alias=ingredient.alias or [],
            description=ingredient.description,
            is_additive=ingredient.is_additive or False,
            additive_code=ingredient.additive_code,
            standard_code=ingredient.standard_code,
            who_level=ingredient.who_level,
            allergen_info=ingredient.allergen_info or [],
            function_type=ingredient.function_type or [],
            origin_type=ingredient.origin_type,
            limit_usage=ingredient.limit_usage,
            legal_region=ingredient.legal_region,
            cas=ingredient.cas,
            applications=ingredient.applications,
            notes=ingredient.notes,
            safety_info=ingredient.safety_info,
            analyses=[],
            related_products=[],
        )

    async def create(self, body: IngredientCreate) -> IngredientResponse:
        """Upsert：按 name 查找，存在则合并，不存在则创建."""
        ingredient = await self._repo.upsert(**body.model_dump())
        return self._to_response(ingredient)

    async def get_by_id(self, ingredient_id: int) -> IngredientResponse | None:
        ingredient = await self._repo.fetch_by_id(ingredient_id)
        if ingredient is None:
            return None
        return self._to_response(ingredient)

    async def list_(
        self,
        limit: int = 20,
        offset: int = 0,
        name: str | None = None,
        is_additive: bool | None = None,
    ) -> tuple[list[IngredientResponse], int]:
        ingredients, total = await self._repo.fetch_list(
            limit=limit,
            offset=offset,
            name=name,
            is_additive=is_additive,
        )
        return [self._to_response(i) for i in ingredients], total

    async def update_full(self, ingredient_id: int, body: IngredientUpdate) -> IngredientResponse | None:
        ingredient = await self._repo.update_full(ingredient_id, **body.model_dump())
        if ingredient is None:
            return None
        return self._to_response(ingredient)

    async def update_partial(self, ingredient_id: int, body: IngredientPatch) -> IngredientResponse | None:
        ingredient = await self._repo.update_partial(
            ingredient_id,
            **{k: v for k, v in body.model_dump().items() if v is not None},
        )
        if ingredient is None:
            return None
        return self._to_response(ingredient)

    async def delete(self, ingredient_id: int) -> bool:
        """软删除，幂等."""
        return await self._repo.soft_delete(ingredient_id)
