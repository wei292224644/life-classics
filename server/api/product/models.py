from pydantic import BaseModel

from enums import RiskLevel


# ── 配料详情（/api/ingredient/{id} 用）─────────────────────────────────────────

class IngredientAnalysis(BaseModel):
    """配料分析结果."""

    id: int
    analysis_type: str
    result: str
    source: str | None
    level: RiskLevel
    confidence_score: int


class IngredientResponse(BaseModel):
    """配料完整信息（API 输出用）."""

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


# ── 产品接口（/api/product 用）───────────────────────────────────────────────

class ProductIngredientAnalysis(BaseModel):
    level: RiskLevel
    reason: str | None


class ProductIngredient(BaseModel):
    """配料简要信息（扁平结构，API 输出用）."""

    id: int
    name: str
    level: RiskLevel
    reason: str | None


class NutritionResponse(BaseModel):
    name: str
    value: str
    value_unit: str
    reference_unit: str


class AnalysisResponse(BaseModel):
    analysis_type: str
    result: str
    source: str | None
    level: RiskLevel
    confidence_score: int


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
