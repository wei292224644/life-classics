from pydantic import BaseModel


class IngredientAnalysis(BaseModel):
    id: int
    analysis_type: str
    results: dict
    level: str


class IngredientResponse(BaseModel):
    id: int
    name: str
    alias: list[str]
    is_additive: bool
    additive_code: str | None
    who_level: str | None
    allergen_info: str | None
    function_type: str | None
    standard_code: str | None
    analysis: IngredientAnalysis | None


class ProductIngredientAnalysis(BaseModel):
    level: str
    reason: str | None


class ProductIngredient(BaseModel):
    id: int
    name: str
    who_level: str | None
    function_type: str | None
    allergen_info: str | None
    analysis: "ProductIngredientAnalysis | None"


class NutritionResponse(BaseModel):
    name: str
    alias: list[str]
    value: str
    value_unit: str
    reference_type: str
    reference_unit: str


class AnalysisResponse(BaseModel):
    id: int
    analysis_type: str
    results: dict
    level: str


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
    analysis: list[AnalysisResponse]
