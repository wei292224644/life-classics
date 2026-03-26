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
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import selectinload

from database.models import Food, Ingredient, FoodIngredient, AnalysisDetail
from database.session import _session_factory

INGREDIENT_TEMPLATES = [
    # 无 AnalysisDetail → 前端 "暂无评级"
    {"name": "卡拉胶",     "additive_code": "E407",  "function_type": "增稠剂", "who_level": None,  "has_analysis": False},
    {"name": "淀粉",       "additive_code": None,     "function_type": None,      "who_level": None,  "has_analysis": False},
    {"name": "食用盐",     "additive_code": None,     "function_type": None,      "who_level": None,  "has_analysis": False},
    # 有 AnalysisDetail → 前端有评级
    {"name": "谷氨酸钠",   "additive_code": "E621",  "function_type": "增味剂", "who_level": "Group 3", "has_analysis": True},
    {"name": "诱惑红",     "additive_code": "E129",  "function_type": "着色剂", "who_level": "Group 3", "has_analysis": True},
    {"name": "苯甲酸钠",   "additive_code": "E211",  "function_type": "防腐剂", "who_level": "Group 2B", "has_analysis": True},
    {"name": "糖精钠",     "additive_code": "E954",  "function_type": "甜味剂", "who_level": "Group 2B", "has_analysis": True},
    {"name": "胭脂红",     "additive_code": "E124",  "function_type": "着色剂", "who_level": "Group 2B", "has_analysis": True},
    {"name": "柠檬黄",     "additive_code": "E102",  "function_type": "着色剂", "who_level": "Group 2B", "has_analysis": True},
    {"name": "亚硝酸钠",   "additive_code": "E250",  "function_type": "护色剂", "who_level": "Group 2A", "has_analysis": True},
    {"name": "香兰素",     "additive_code": "E107",  "function_type": "香料",   "who_level": "Group 3", "has_analysis": True},
    {"name": "焦糖色",     "additive_code": "E150a", "function_type": "着色剂", "who_level": "Group 3", "has_analysis": True},
]

LEVEL_MAP: dict[str | None, str] = {
    "Group 1": "t4",
    "Group 2A": "t3",
    "Group 2B": "t2",
    "Group 3": "t1",
    "Group 4": "t0",
    None: "unknown",
}


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
               :who_level, NULL, '{}'::JSONB, NULL, NULL, NULL, NULL, NULL)
            RETURNING id
        """),
        {
            "name":          data["name"],
            "is_additive":   data["additive_code"] is not None,
            "additive_code": data["additive_code"],
            "function_type": data["function_type"],
            "who_level":     data["who_level"],
        }
    )
    return result.fetchone()[0]


async def upsert_analysis(session, ingredient_id: int, who_level: str | None) -> None:
    """插入 ingredient_summary analysis（幂等）。"""
    result = await session.execute(
        select(AnalysisDetail).where(
            AnalysisDetail.target_id == ingredient_id,
            AnalysisDetail.analysis_target == "ingredient",
            AnalysisDetail.analysis_type == "ingredient_summary",
        )
    )
    if result.scalar_one_or_none():
        return

    result_text = "mock summary"
    source_text = "WHO mock source"
    level = LEVEL_MAP.get(who_level, "unknown")
    uid = str(uuid4())

    await session.execute(
        text("""
            INSERT INTO analysis_details
              (target_id, analysis_target, analysis_type, analysis_version,
               ai_model, result, source, level, confidence_score, raw_output, created_by_user)
            VALUES
              (:tid, 'ingredient', 'ingredient_summary', 'v1',
               'faker-seed', :result, :source, :level, 80, '{}'::JSONB, CAST(:uid AS UUID))
        """),
        {"tid": ingredient_id, "result": result_text, "source": source_text, "level": level, "uid": uid}
    )


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

            if template["has_analysis"]:
                await upsert_analysis(session, ing_id, template["who_level"])
                print(f"  [有评级] {template['name']} ({template['additive_code'] or '-'}): {template['who_level']}")
            else:
                print(f"  [无评级] {template['name']} → 前端显示「暂无评级」")

            await link_ingredient(session, FOOD_ID, ing_id)

        await session.commit()
        print("\nDone. 打开产品页配料信息，检查是否有「暂无评级」分组。")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
