"""Repository for ProductAnalysis CRUD operations."""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ProductAnalysis

if TYPE_CHECKING:
    pass


class ProductAnalysisRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_food_id(
        self,
        food_id: int,
    ) -> ProductAnalysis | None:
        """Query product_analyses WHERE food_id = :food_id AND deleted_at IS NULL."""
        result = await self._session.execute(
            select(ProductAnalysis).where(
                ProductAnalysis.food_id == food_id,
                ProductAnalysis.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def insert_if_absent(
        self,
        food_id: int,
        data: dict,
        created_by_user: str,
    ) -> tuple[ProductAnalysis, Literal["inserted", "already_exists"]]:
        """
        Insert a new ProductAnalysis if no active record exists for this food_id.

        1. Query by food_id — if exists return (existing, "already_exists").
        2. Otherwise INSERT and return (new, "inserted").
        3. On UniqueViolation (concurrent insert) — re-fetch and return (existing, "already_exists").
        """
        existing = await self.get_by_food_id(food_id)
        if existing is not None:
            return existing, "already_exists"

        new_record = ProductAnalysis(
            food_id=food_id,
            ai_model=data["ai_model"],
            version=data["version"],
            level=data["level"],
            description=data["description"],
            advice=data["advice"],
            demographics=data.get("demographics", []),
            scenarios=data.get("scenarios", []),
            references=data.get("references", []),
            created_by_user=created_by_user,
        )
        self._session.add(new_record)

        try:
            await self._session.flush()
            return new_record, "inserted"
        except Exception as exc:  # noqa: BLE001
            await self._session.rollback()
            existing = await self.get_by_food_id(food_id)
            if existing is not None:
                return existing, "already_exists"
            raise exc
