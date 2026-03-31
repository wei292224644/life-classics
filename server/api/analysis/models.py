"""API models for analysis endpoints."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from workflow_product_analysis.types import (
    AnalysisError,
    AnalysisStatus,
    ProductAnalysisResult,
)


class StartAnalysisRequest(BaseModel):
    food_id: int | None = None


class StartAnalysisResponse(BaseModel):
    task_id: str


class AnalysisStatusResponse(BaseModel):
    task_id: str
    status: AnalysisStatus
    error: AnalysisError | None = None
    result: ProductAnalysisResult | None = None


class FeedbackRequest(BaseModel):
    task_id: str | None = None
    food_id: int
    category: Literal["ocr_wrong", "verdict_wrong", "ingredient_wrong", "other"]
    message: str | None = None
    client_context: dict | None = None


class FeedbackResponse(BaseModel):
    accepted: bool
