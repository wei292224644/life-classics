"""API models for ingredient_alias."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AliasCreateRequest(BaseModel):
    """创建别名请求."""

    ingredient_id: int = Field(..., description="关联的配料 ID")
    alias: str = Field(..., min_length=1, max_length=255, description="别名文本")
    alias_type: Literal["chinese", "english", "abbreviation", "folk_name"] = Field(
        default="chinese", description="别名类型"
    )


class AliasResponse(BaseModel):
    """别名响应."""

    id: int
    ingredient_id: int
    alias: str
    alias_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AliasListResponse(BaseModel):
    """别名列表响应."""

    items: list[AliasResponse]
    total: int
