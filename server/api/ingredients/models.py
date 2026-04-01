from pydantic import BaseModel, Field

from enums import WhoLevel


class IngredientCreate(BaseModel):
    """创建/更新配料请求体（upsert 用）."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_additive: bool | None = None
    additive_code: str | None = None
    standard_code: str | None = None
    who_level: WhoLevel | None = None
    allergen_info: list[str] = []
    function_type: list[str] = []
    origin_type: str | None = None
    limit_usage: str | None = None
    legal_region: str | None = None
    cas: str | None = None
    applications: str | None = None
    notes: str | None = None
    safety_info: str | None = None


class IngredientUpdate(BaseModel):
    """全量更新请求体（PUT 用，所有字段必填）."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_additive: bool | None = None
    additive_code: str | None = None
    standard_code: str | None = None
    who_level: WhoLevel | None = None
    allergen_info: list[str] = []
    function_type: list[str] = []
    origin_type: str | None = None
    limit_usage: str | None = None
    legal_region: str | None = None
    cas: str | None = None
    applications: str | None = None
    notes: str | None = None
    safety_info: str | None = None


class IngredientPatch(BaseModel):
    """部分更新请求体（PATCH 用，所有字段可选）."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_additive: bool | None = None
    additive_code: str | None = None
    standard_code: str | None = None
    who_level: WhoLevel | None = None
    allergen_info: list[str] | None = None
    function_type: list[str] | None = None
    origin_type: str | None = None
    limit_usage: str | None = None
    legal_region: str | None = None
    cas: str | None = None
    applications: str | None = None
    notes: str | None = None
    safety_info: str | None = None


class RelatedProductSimple(BaseModel):
    """配料关联的简化产品信息"""
    id: int
    name: str
    barcode: str
    image_url: str | None
    category: str | None


class IngredientResponse(BaseModel):
    """配料完整信息（API 输出用）."""

    id: int
    name: str
    alias: list[str]
    description: str | None
    is_additive: bool
    additive_code: str | None
    standard_code: str | None
    who_level: str | None
    allergen_info: list[str]
    function_type: list[str]
    origin_type: str | None
    limit_usage: str | None
    legal_region: str | None
    cas: str | None
    applications: str | None
    notes: str | None
    safety_info: str | None
    analyses: list  # 保留字段，暂无数据源
    related_products: list[RelatedProductSimple] = []


class IngredientsListResponse(BaseModel):
    """配料列表响应."""
    items: list[IngredientResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
