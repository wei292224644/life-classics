"""API models for analysis endpoints."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class StartAnalysisRequest(BaseModel):
    food_id: int | None = None


class StartAnalysisResponse(BaseModel):
    task_id: str


# L1 层自有的 status enum，不引用 Infra types
AnalysisStatus = Literal["pending", "processing", "completed", "failed"]


class AnalysisStatusResponse(BaseModel):
    task_id: str
    status: AnalysisStatus
    error: str | None = None
    result: dict[str, Any] | None = None


class FeedbackRequest(BaseModel):
    task_id: str | None = None
    food_id: int
    category: Literal["ocr_wrong", "verdict_wrong", "ingredient_wrong", "other"]
    message: str | None = None
    client_context: dict | None = None


class FeedbackResponse(BaseModel):
    accepted: bool
