"""Pydantic models for ingredient_analysis API."""
from __future__ import annotations

from pydantic import BaseModel


class IngredientAnalysisCreate(BaseModel):
    ai_model: str
    level: str
    safety_info: str
    alternatives: list
    confidence_score: float
    evidence_refs: list
    decision_trace: dict


class IngredientAnalysisResponse(BaseModel):
    id: int
    ingredient_id: int
    ai_model: str
    level: str
    safety_info: str
    alternatives: list
    confidence_score: float
    created_at: str