"""
Seed 脚本：为数据库填充测试数据（配料风险等级全覆盖 + unknown 验证）。

用法：
    cd server
    uv run python db_repositories/seed_data.py

TODO: 上线前删除此脚本。
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from database.models import Food, Ingredient, FoodIngredient
from database.session import _session_factory

INGREDIENT_TEMPLATES = [
    {"name": "卡拉胶",  "additive_code": "E407",  "function_type": "增稠剂"},
    {"name": "淀粉",    "additive_code": None,     "function_type": None},
    {"name": "食用盐",  "additive_code": None,     "function_type": None},
    {"name": "谷氨酸钠", "additive_code": "E621",  "function_type": "增味剂"},
    {"name": "诱惑红",  "additive_code": "E129",  "function_type": "着色剂"},
    {"name": "苯甲酸钠", "additive_code": "E211",  "function_type": "防腐剂"},
    {"name": "糖精钠",  "additive_code": "E954",  "function_type": "甜味剂"},
    {"name": "胭脂红",  "additive_code": "E124",  "function_type": "着色剂"},
    {"name": "柠檬黄",  "additive_code": "E102",  "function_type": "着色剂"},
    {"name": "亚硝酸钠", "additive_code": "E250",  "function_type": "护色剂"},
    {"name": "香兰素",  "additive_code": "E107",  "function_type": "香料"},
    {"name": "焦糖色",  "additive_code": "E150a", "function_type": "着色剂"},
]


async def upsert_ingredient(session, data: dict) -> int:
    """插入或获取配料，返回 ingredient.id。"""
    result = await session.execute(
        select(Ingredient).where(Ingredient.name == data["name"])
    )
    ing = result.scalar_one_or_none()
    if ing:
        return ing.id

    # 用 raw SQL 避免 SQLAlchemy ORM 层面对 who_level enum 默认值的类型检查问题
    result = await session.execute(
        text("""
            INSERT INTO ingredients
              (name, alias, is_additive, additive_code, function_type,
               who_level, allergen_info, metadata, origin_type, limit_usage,
               legal_region, standard_code, description)
            VALUES
              (:name, ARRAY[]::VARCHAR(255)[], :is_additive, :additive_code, :function_type,
               NULL, NULL, '{}'::JSONB, NULL, NULL, NULL, NULL, NULL)
            RETURNING id
        """),
        {
            "name":          data["name"],
            "is_additive":   data["additive_code"] is not None,
            "additive_code": data["additive_code"],
            "function_type": data["function_type"],
        }
    )
    return result.fetchone()[0]


async def link_ingredient(session, food_id: int, ingredient_id: int) -> None:
    """关联配料到产品（幂等）。"""
    result = await session.execute(
        select(FoodIngredient).where(
            FoodIngredient.food_id == food_id,
            FoodIngredient.ingredient_id == ingredient_id,
        )
    )
    if result.scalar_one_or_none():
        return

    await session.execute(
        text("""
            INSERT INTO food_ingredients (food_id, ingredient_id, created_by_user)
            VALUES (:fid, :iid, CAST(:uid AS UUID))
        """),
        {"fid": food_id, "iid": ingredient_id, "uid": str(uuid4())}
    )


async def main() -> None:
    FOOD_ID = 101  # 经典苏打饼干

    async with _session_factory() as session:
        # 确认产品存在
        result = await session.execute(
            select(Food).where(Food.id == FOOD_ID).options(selectinload(Food.food_ingredients))
        )
        food = result.scalar_one_or_none()
        if not food:
            print(f"Food id={FOOD_ID} not found")
            return
        print(f"Product: {food.name} (id={food.id})")

        for template in INGREDIENT_TEMPLATES:
            ing_id = await upsert_ingredient(session, template)
            print(f"  {template['name']} ({template['additive_code'] or '-'}): 已插入/已存在")
            await link_ingredient(session, FOOD_ID, ing_id)

        await session.commit()
        print("\nDone.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
