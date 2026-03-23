"""
Seed 脚本：为数据库填充测试数据（配料风险等级全覆盖 + unknown 验证）。

用法：
    cd server
    uv run python db_repositories/seed_data.py

TODO: 上线前删除此脚本。
"""

from __future__ import annotations

from uuid import uuid4

from faker import Faker
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models import Food, Ingredient, FoodIngredient, AnalysisDetail
from database.session import _session_factory

FAKER = Faker("zh_CN")

# ── 配料模板（部分有 analysis，部分无 → 前端 unknown）───────────────────────────

INGREDIENT_TEMPLATES = [
    # 有风险等级
    {"name": "卡拉胶", "additive_code": "E407", "function_type": "增稠剂", "who_level": None, "has_analysis": False},
    {"name": "谷氨酸钠", "additive_code": "E621", "function_type": "增味剂", "who_level": "Group 3", "has_analysis": True},
    {"name": "诱惑红", "additive_code": "E129", "function_type": "着色剂", "who_level": "Group 3", "has_analysis": True},
    {"name": "苯甲酸钠", "additive_code": "E211", "function_type": "防腐剂", "who_level": "Group 2B", "has_analysis": True},
    {"name": "糖精钠", "additive_code": "E954", "function_type": "甜味剂", "who_level": "Group 2B", "has_analysis": True},
    {"name": "胭脂红", "additive_code": "E124", "function_type": "着色剂", "who_level": "Group 2B", "has_analysis": True},
    {"name": "柠檬黄", "additive_code": "E102", "function_type": "着色剂", "who_level": "Group 2B", "has_analysis": True},
    {"name": "亚硝酸钠", "additive_code": "E250", "function_type": "护色剂", "who_level": "Group 2A", "has_analysis": True},
    {"name": "植物奶油", "additive_code": None, "function_type": None, "who_level": None, "has_analysis": True},
    {"name": "香兰素", "additive_code": "E107", "function_type": "香料", "who_level": None, "has_analysis": True},
    {"name": "果葡糖浆", "additive_code": None, "function_type": None, "who_level": None, "has_analysis": True},
    {"name": "焦糖色", "additive_code": "E150a", "function_type": "着色剂", "who_level": "Group 3", "has_analysis": True},
    # 无 analysis → 前端显示 unknown
    {"name": "淀粉", "additive_code": None, "function_type": None, "who_level": None, "has_analysis": False},
    {"name": "食用盐", "additive_code": None, "function_type": None, "who_level": None, "has_analysis": False},
]

# analysis.level 映射
LEVEL_MAP: dict[str | None, str] = {
    "Group 1": "t4",
    "Group 2A": "t3",
    "Group 2B": "t2",
    "Group 3": "t1",
    "Group 4": "t0",
    None: "unknown",
}


async def upsert_ingredient(session, data: dict) -> Ingredient:
    """插入或更新配料，返回 ingredient 对象。"""
    result = await session.execute(
        select(Ingredient).where(Ingredient.name == data["name"])
    )
    ing = result.scalar_one_or_none()
    if ing:
        return ing

    ing = Ingredient(
        name=data["name"],
        is_additive=data["additive_code"] is not None,
        additive_code=data["additive_code"],
        function_type=data["function_type"],
        who_level=data["who_level"],
        allergen_info=None,
    )
    session.add(ing)
    await session.flush()
    return ing


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
        return  # 已存在，跳过

    level = LEVEL_MAP.get(who_level, "unknown")
    analysis = AnalysisDetail(
        target_id=ingredient_id,
        analysis_target="ingredient",
        analysis_type="ingredient_summary",
        analysis_version="v1",
        ai_model="mock-model",
        results={"summary": "mock summary", "reason": "mock reason"},
        level=level,
        confidence_score=80,
        raw_output={},
        created_by_user=uuid4(),
    )
    session.add(analysis)


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

    link = FoodIngredient(
        food_id=food_id,
        ingredient_id=ingredient_id,
        created_by_user=uuid4(),
    )
    session.add(link)


async def main() -> None:
    async with _session_factory() as session:
        # 找到测试产品
        result = await session.execute(
            select(Food)
            .where(Food.barcode == "6900000000001")
            .options(selectinload(Food.food_ingredients))
        )
        food = result.scalar_one_or_none()
        if not food:
            print("Product 6900000000001 not found")
            return

        print(f"Found product: {food.name} (id={food.id})")

        for template in INGREDIENT_TEMPLATES:
            ing = await upsert_ingredient(session, template)

            if template["has_analysis"]:
                await upsert_analysis(session, ing.id, template["who_level"])
                print(f"  [有评级] {ing.name} ({ing.additive_code or '-'}): {template['who_level']}")
            else:
                print(f"  [无评级] {ing.name} → 前端显示 unknown")

            await link_ingredient(session, food.id, ing.id)

        await session.commit()
        print("\nDone. 打开产品页配料信息，检查是否有「暂无评级」分组。")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
