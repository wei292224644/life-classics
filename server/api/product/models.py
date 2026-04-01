from pydantic import BaseModel


class ProductIngredient(BaseModel):
    """配料简要信息（扁平结构，API 输出用）."""

    id: int
    name: str


class NutritionResponse(BaseModel):
    name: str
    value: str
    value_unit: str
    reference_unit: str


class ProductResponse(BaseModel):
    id: int
    barcode: str
    name: str
    manufacturer: str | None
    origin_place: str | None
    shelf_life: str | None
    net_content: str | None
    image_url_list: list[str]
    nutritions: list[NutritionResponse]
    ingredients: list[ProductIngredient]
