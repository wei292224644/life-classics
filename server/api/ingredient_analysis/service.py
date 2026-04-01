"""Service layer for ingredient_analysis API — DB writes only."""
from __future__ import annotations

from config import settings
from db_repositories.ingredient_analysis import IngredientAnalysisRepository


class IngredientAnalysisService:
    def __init__(self, session):
        self._repo = IngredientAnalysisRepository(session)

    async def create(self, ingredient_id: int, data: dict) -> dict:
        record = await self._repo.insert_new_version(
            ingredient_id=ingredient_id,
            data=data,
            created_by_user=settings.SYSTEM_USER_ID,
        )
        return {
            "id": record.id,
            "ingredient_id": record.ingredient_id,
            "ai_model": record.ai_model,
            "level": record.level,
            "safety_info": record.safety_info,
            "alternatives": record.alternatives,
            "confidence_score": record.confidence_score,
            "created_at": record.created_at.isoformat(),
        }