"""Repository for IngredientAnalysis CRUD operations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import IngredientAnalysis

if TYPE_CHECKING:
    pass


async def get_active_by_ingredient_id(
    ingredient_id: int,
    session: AsyncSession,
) -> IngredientAnalysis | None:
    """
    Query ingredient_analyses WHERE ingredient_id = :id AND is_active = True AND deleted_at IS NULL.
    Returns the single active record or None.
    """
    result = await session.execute(
        select(IngredientAnalysis).where(
            IngredientAnalysis.ingredient_id == ingredient_id,
            IngredientAnalysis.is_active.is_(True),
            IngredientAnalysis.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def insert_new_version(
    ingredient_id: int,
    data: dict,
    created_by_user: str,
    session: AsyncSession,
) -> IngredientAnalysis:
    """
    Append-only version insert for ingredient analysis.

    1. Deactivate all is_active=True rows for this ingredient_id.
    2. INSERT a new row with is_active=True.
    3. Return the new row.
    """
    # Deactivate existing active rows
    await session.execute(
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
        version=data["version"],
        level=data.get("level", "unknown"),
        safety_info=data.get("safety_info", ""),
        alternatives=data.get("alternatives", []),
        confidence_score=data.get("confidence_score", 0.0),
        evidence_refs=data.get("evidence_refs", []),
        decision_trace=data.get("decision_trace", {}),
        is_active=True,
        created_by_user=created_by_user,
    )
    session.add(new_record)
    await session.flush()
    return new_record


async def get_history_by_ingredient_id(
    ingredient_id: int,
    session: AsyncSession,
) -> list[IngredientAnalysis]:
    """
    Query all non-deleted versions of ingredient analysis, ordered by created_at DESC.
    """
    result = await session.execute(
        select(IngredientAnalysis)
        .where(
            IngredientAnalysis.ingredient_id == ingredient_id,
            IngredientAnalysis.deleted_at.is_(None),
        )
        .order_by(IngredientAnalysis.created_at.desc())
    )
    return list(result.scalars().all())
