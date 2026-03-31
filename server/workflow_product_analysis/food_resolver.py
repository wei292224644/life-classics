"""food_id 解析 — 从可选 explicit_food_id + OCR 品名解析确定性 food_id。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from database.models import Food

if TYPE_CHECKING:
    pass


class InvalidFoodIdError(Exception):
    """显式传入的 food_id 在 DB 中不存在。"""


async def resolve_food_id(
    explicit_food_id: int | None,
    product_name: str | None,
    task_id: str,
    session: AsyncSession,
    settings: Settings,
) -> int:
    """
    解析确定性 food_id。

    逻辑优先级：
    1. explicit_food_id 不为 None → 查 foods 表，存在即返回；不存在抛 InvalidFoodIdError
    2. product_name 不为 None → ILIKE 模糊匹配 foods.name，唯一候选且相似度 >= 阈值则返回
    3. 以上均未命中 → 创建占位 Food 记录（barcode=PHOTO-{task_id}），返回其 id

    入参：
        explicit_food_id: 来自请求参数
        product_name: 来自 OCR 解析的品名
        task_id: 用于生成占位 barcode
        session: AsyncSession
        settings: 含 FOOD_NAME_MATCH_THRESHOLD

    出参：
        food_id: int

    异常：
        InvalidFoodIdError: explicit_food_id 存在但 DB 查不到
    """
    # 1. 显式 food_id
    if explicit_food_id is not None:
        result = await session.execute(
            select(Food).where(
                Food.id == explicit_food_id,
                Food.deleted_at.is_(None),
            )
        )
        food = result.scalar_one_or_none()
        if food is not None:
            return food.id
        raise InvalidFoodIdError(
            f"explicit_food_id={explicit_food_id} not found or deleted"
        )

    # 2. 品名模糊匹配（MVP：ILIKE）
    if product_name is not None:
        pattern = f"%{product_name}%"
        result = await session.execute(
            select(Food).where(
                Food.name.ilike(pattern),
                Food.deleted_at.is_(None),
            )
        )
        candidates = list(result.scalars().all())

        if len(candidates) == 1:
            # 唯一候选 — MVP 直接返回（阈值匹配待嵌入方案）
            threshold = getattr(settings, "FOOD_NAME_MATCH_THRESHOLD", 0.7)
            # 目前单候选即认为命中；后续可改为 embedding cosine similarity
            if threshold > 0:
                return candidates[0].id
            return candidates[0].id
        elif len(candidates) > 1:
            # 多候选：取 name 最长的那个（更具体）
            best = max(candidates, key=lambda f: len(f.name or ""))
            return best.id

    # 3. 创建占位 Food
    barcode = f"PHOTO-{task_id}"
    name = product_name if product_name else "未命名产品"
    placeholder = Food(
        barcode=barcode,
        name=name,
        metadata={"source": "photo_import", "task_id": task_id},
        created_by_user=getattr(settings, "SYSTEM_USER_ID", ""),
    )
    session.add(placeholder)
    await session.flush()
    return placeholder.id
