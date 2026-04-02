"""Repository for IngredientAnalysis CRUD operations."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import IngredientAnalysis

if TYPE_CHECKING:
    pass


class IngredientAnalysisRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_active_by_ingredient_id(
        self,
        ingredient_id: int,
    ) -> IngredientAnalysis | None:
        """
        Query ingredient_analyses WHERE ingredient_id = :id AND is_active = True AND deleted_at IS NULL.
        Returns the single active record or None.
        """
        result = await self._session.execute(
            select(IngredientAnalysis).where(
                IngredientAnalysis.ingredient_id == ingredient_id,
                IngredientAnalysis.is_active.is_(True),
                IngredientAnalysis.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def insert_new_version(
        self,
        ingredient_id: int,
        data: dict,
        created_by_user: str,
    ) -> IngredientAnalysis:
        """
        Append-only version insert for ingredient analysis.

        1. Deactivate all is_active=True rows for this ingredient_id.
        2. INSERT a new row with is_active=True.
        3. Return the new row.
        """
        await self._session.execute(
            update(IngredientAnalysis)
            .where(
                IngredientAnalysis.ingredient_id == ingredient_id,
                IngredientAnalysis.is_active.is_(True),
                IngredientAnalysis.deleted_at.is_(None),
            )
            .values(is_active=False)
        )

        new_record = IngredientAnalysis(
            ingredient_id=ingredient_id,
            ai_model=data["ai_model"],
            level=data.get("level", "unknown"),
            safety_info=data.get("safety_info", ""),
            alternatives=data.get("alternatives", []),
            confidence_score=data.get("confidence_score", 0.0),
            evidence_refs=data.get("evidence_refs", []),
            decision_trace=data.get("decision_trace", {}),
            is_active=True,
            created_by_user=created_by_user,
        )
        self._session.add(new_record)
        await self._session.flush()
        await self._session.commit()
        return new_record

    async def get_history_by_ingredient_id(
        self,
        ingredient_id: int,
    ) -> list[IngredientAnalysis]:
        """
        Query all non-deleted versions of ingredient analysis, ordered by created_at DESC.
        """
        result = await self._session.execute(
            select(IngredientAnalysis)
            .where(
                IngredientAnalysis.ingredient_id == ingredient_id,
                IngredientAnalysis.deleted_at.is_(None),
            )
            .order_by(IngredientAnalysis.created_at.desc())
        )
        return list(result.scalars().all())

    async def fetch_by_ingredient_ids(
        self, ingredient_ids: list[int]
    ) -> list[IngredientAnalysis]:
        """批量查询活跃的 IngredientAnalysis，用于 assembler 预填充数据."""
        if not ingredient_ids:
            return []
        result = await self._session.execute(
            select(IngredientAnalysis).where(
                IngredientAnalysis.ingredient_id.in_(ingredient_ids),
                IngredientAnalysis.is_active.is_(True),
                IngredientAnalysis.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())
