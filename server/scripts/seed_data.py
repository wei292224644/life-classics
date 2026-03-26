"""
Seed 脚本：向 PostgreSQL 插入大量假数据，供前端联调使用。

用法：
    cd server
    uv run python scripts/seed_data.py

依赖：
    pip install faker
    （已在 pyproject.toml 中声明 faker）
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime

# 确保 server/ 目录在 sys.path 中（支持 `python scripts/seed_data.py` 方式运行）
_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from faker import Faker

# 初始化中文 Faker
fake = Faker("zh_CN")
# 固定 seed，保证每次运行生成相同数据（方便复现）
Faker.seed(42)

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import _session_factory
from database.models import (
    Food,
    Ingredient,
    FoodIngredient,
    NutritionTable,
    FoodNutritionEntry,
    AnalysisDetail,
)
from enums import RiskLevel


# ── 固定 UUID（模拟同一个系统用户）───────────────────────────────────────────

SYSTEM_USER = uuid.UUID("00000000-0000-0000-0000-000000000000")


# ── 数据生成函数 ────────────────────────────────────────────────────────────

def make_food(index: int) -> Food:
    """生成一条 Food 记录。"""
    categories = [
        "零食", "饮料", "调味品", "乳制品", "肉制品",
        "糕点", "糖果", "方便食品", "坚果炒货", "酒类",
    ]
    manufacturers = [
        "伊利实业集团有限公司", "蒙牛乳业（集团）股份有限公司", "康师傅控股有限公司",
        "统一企业（中国）投资有限公司", "娃哈哈集团有限公司", "农夫山泉股份有限公司",
        "可口可乐饮料（上海）有限公司", "百事可乐（中国）有限公司", "亿滋（中国）有限公司",
        "上海太太乐食品有限公司", "李锦记（广州）食品有限公司", "海底捞调味品有限公司",
    ]
    return Food(
        barcode=f"69{str(index + 1).zfill(10)}",
        name=fake.catch_phrase() + " " + fake.random_element(elements=["礼盒装", "家庭装", "迷你装", "量贩装", ""]),
        image_url_list=[
            f"https://picsum.photos/seed/{index}/400/400",
            f"https://picsum.photos/seed/{index + 1000}/400/400",
        ],
        manufacturer=fake.random_element(manufacturers),
        production_address=fake.address(),
        origin_place=fake.random_element(["中国", "日本", "韩国", "美国", "德国", "意大利", "法国"]),
        production_license=f"SC{str(fake.random_int(min=100000, max=999999))}",
        product_category=fake.random_element(categories),
        product_standard_code=f"GB/T {fake.random_int(min=1000, max=9999)}",
        shelf_life=f"{fake.random_int(min=6, max=36)}个月",
        net_content=f"{fake.random_int(min=50, max=5000)}g",
        created_by_user=SYSTEM_USER,
    )


def make_ingredient(index: int) -> Ingredient:
    """生成一条 Ingredient 记录。"""
    additive_codes = [None, "F202", "E330", "E951", "E500", "E452", "E300", "E322"]
    who_levels = ["Group 1", "Group 2A", "Group 2B", "Group 3", "Group 4"]
    function_types = [
        "防腐剂", "增稠剂", "乳化剂", "抗氧化剂", "着色剂",
        "甜味剂", "酸度调节剂", "香料", "营养强化剂", "稳定剂",
    ]
    is_additive = fake.boolean(chance_of_getting_true=60)
    return Ingredient(
        name=fake.unique.first_name() + fake.random_element(["酸", "酯", "醇", "盐", "糖", "素"]),
        alias=[fake.name(), fake.name()] if fake.boolean() else [],
        description=fake.text(max_nb_chars=120) if fake.boolean() else None,
        is_additive=is_additive,
        additive_code=fake.random_element(additive_codes) if is_additive else None,
        standard_code=f"GB {fake.random_int(min=1000, max=9999)}" if fake.boolean() else None,
        who_level=fake.random_element(who_levels),
        allergen_info=fake.random_element([
            "含有麸质", "含有乳糖", "含有大豆", "含有花生", "含有甲壳类",
            "含有鱼类", "含有蛋类", "含有坚果", None, None, None,
        ]),
        function_type=fake.random_element(function_types),
        origin_type=fake.random_element(["天然", "合成", "半合成", None]),
        limit_usage=f"{fake.random_int(1, 100)}mg/kg" if fake.boolean() else None,
        legal_region=fake.random_element(["中国", "欧盟", "美国", "日本", "Codex"]),
    )


def make_nutrition(index: int) -> NutritionTable:
    """生成一条 NutritionTable 记录。"""
    categories = ["宏量营养素", "维生素", "矿物质", "膳食纤维", "其他"]
    return NutritionTable(
        name=fake.random_element([
            "能量", "蛋白质", "脂肪", "碳水化合物", "膳食纤维",
            "维生素A", "维生素C", "维生素D", "维生素E", "维生素B1",
            "钙", "铁", "锌", "钠", "钾", "镁", "磷", "硒",
        ]),
        alias=[fake.word()] if fake.boolean() else [],
        category=fake.random_element(categories),
        sub_category=fake.random_element(categories) if fake.boolean() else None,
        description=fake.sentence(nb_words=10) if fake.boolean() else None,
        daily_value=f"{fake.random_int(10, 2000)}{fake.random_element(['mg', 'g', 'μg', 'kJ'])}",
        upper_limit=f"{fake.random_int(1000, 5000)}{fake.random_element(['mg', 'g'])}" if fake.boolean() else None,
        is_essential=fake.boolean(chance_of_getting_true=70),
        risk_info=fake.text(max_nb_chars=80) if fake.boolean() else None,
        pregnancy_note=fake.sentence(nb_words=15) if fake.boolean() else None,
        metabolism_role=fake.random_element([
            "能量来源", "组织修复", "免疫功能", "骨骼健康", "血红蛋白合成",
            "抗氧化", "酶的辅因子", "神经传导", "水平衡", "糖代谢",
        ]),
        created_by_user=SYSTEM_USER,
    )


def make_food_ingredient(food_id: int, ingredient_id: int) -> FoodIngredient:
    """生成一条 FoodIngredient 关联记录。"""
    levels = ["t4", "t3", "t2", "t1", "t0", "unknown"]
    reasons = [
        "在允许范围内使用，符合国家标准",
        "天然存在，非人为添加",
        "适量摄入对人体无害",
        None,
        None,
    ]
    return FoodIngredient(
        food_id=food_id,
        ingredient_id=ingredient_id,
        created_by_user=SYSTEM_USER,
    )


def make_food_nutrition(food_id: int, nutrition_id: int) -> FoodNutritionEntry:
    """生成一条 FoodNutritionEntry 记录。"""
    units = ["g", "mg", "kcal", "mL", "kJ"]
    ref_types = ["PER_100_WEIGHT", "PER_100_ENERGY", "PER_SERVING", "PER_DAY"]
    ref_units = ["g", "mg", "kcal", "mL", "kJ", "serving", "day"]
    return FoodNutritionEntry(
        food_id=food_id,
        nutrition_id=nutrition_id,
        value=round(fake.random.uniform(0.1, 500.0), 2),
        value_unit=fake.random_element(units),
        reference_type=fake.random_element(ref_types),
        reference_unit=fake.random_element(ref_units),
        created_by_user=SYSTEM_USER,
    )


def make_analysis_detail(target_id: int, target_type: str, index: int, analysis_type: str | None = None) -> AnalysisDetail:
    """生成一条 AnalysisDetail 记录。"""
    analysis_types = [
        "usage_advice_summary", "health_summary", "pregnancy_safety",
        "risk_summary", "recent_risk_summary", "ingredient_summary",
    ]
    levels = ["t4", "t3", "t2", "t1", "t0", "unknown"]
    health_benefits = [
        "适量摄入有助于补充人体所需营养素",
        "可促进肠道蠕动，维持肠道健康",
        "为人体提供必需的能量来源",
        "参与代谢过程，有助于维持身体机能",
        "含有的活性成分对健康有一定益处",
    ]
    reasons = [
        "在允许范围内使用，符合国家标准",
        "天然存在，非人为添加",
        "适量摄入对人体无害",
        "经权威机构认证，安全性已验证",
    ]
    risk_factors = [
        "过量摄入可能对特定人群产生不良影响",
        "部分人群可能出现过敏反应",
        "长期大量摄入需注意",
    ]
    suggestions = [
        {"text": "正常烹饪用量在成人中是安全的", "type": "positive"},
        {"text": "特定人群请遵医嘱食用", "type": "conditional"},
        {"text": "注意控制每日摄入量", "type": "warning"},
    ]

    # 如果未指定类型，则随机选择
    if analysis_type is None:
        analysis_type = fake.random_element(analysis_types)

    # result 直接用字符串
    result = fake.sentence(nb_words=15)

    return AnalysisDetail(
        target_id=target_id,
        analysis_target=target_type,
        analysis_type=analysis_type,
        analysis_version="v1",
        ai_model=fake.random_element(["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"]),
        result=result,
        source=fake.random_element(["WHO食品添加剂评估", "FAO/JECFA报告", "EFSA评估报告"]) if fake.random.random() > 0.3 else None,
        level=fake.random_element(levels),
        confidence_score=fake.random_int(min=60, max=99),
        raw_output={
            "model": fake.random_element(["gpt-4o", "gpt-4o-mini"]),
            "finish_reason": "stop",
            "raw_text": fake.text(max_nb_chars=300),
        },
        created_by_user=SYSTEM_USER,
    )


# ── 主函数 ──────────────────────────────────────────────────────────────────

async def _clear_tables(session: AsyncSession) -> None:
    """清空所有相关表（按外键依赖顺序）。"""
    print("正在清空旧数据...")
    await session.execute(delete(FoodNutritionEntry))
    await session.execute(delete(FoodIngredient))
    await session.execute(delete(AnalysisDetail))
    await session.execute(delete(Food))
    await session.execute(delete(Ingredient))
    await session.execute(delete(NutritionTable))
    await session.commit()
    print("清空完成。")


async def seed():
    """生成并插入所有假数据。"""
    async with _session_factory() as session:
        # 清空
        await _clear_tables(session)

        # ── 1. 生成 Ingredient（先生成，因为 Food 依赖它）────────────────
        print("生成 Ingredient 数据...")
        ingredient_count = 80
        ingredients = [make_ingredient(i) for i in range(ingredient_count)]
        session.add_all(ingredients)
        await session.flush()  # 获取 ID

        # 提取 Ingredient.id 用于后续关联
        ingredient_ids = [ing.id for ing in ingredients]
        print(f"  完成：{ingredient_count} 条 Ingredient")

        # ── 2. 生成 NutritionTable ───────────────────────────────────────
        print("生成 NutritionTable 数据...")
        nutrition_count = 30
        nutritions = [make_nutrition(i) for i in range(nutrition_count)]
        session.add_all(nutritions)
        await session.flush()

        nutrition_ids = [n.id for n in nutritions]
        print(f"  完成：{nutrition_count} 条 NutritionTable")

        # ── 3. 生成 Food ──────────────────────────────────────────────────
        print("生成 Food 数据...")
        food_count = 50
        foods = [make_food(i) for i in range(food_count)]
        session.add_all(foods)
        await session.flush()

        food_ids = [f.id for f in foods]
        print(f"  完成：{food_count} 条 Food")

        # ── 4. 生成 FoodIngredient 关联 ──────────────────────────────────
        print("生成 FoodIngredient 关联数据...")
        food_ingredients = []
        for food_id in food_ids:
            # 每个食品随机关联 5~15 个配料
            import random
            random.seed(food_id)  # 保证可复现
            chosen = random.sample(ingredient_ids, k=random.randint(5, min(15, len(ingredient_ids))))
            for ing_id in chosen:
                food_ingredients.append(make_food_ingredient(food_id, ing_id))
        session.add_all(food_ingredients)
        await session.flush()
        print(f"  完成：{len(food_ingredients)} 条 FoodIngredient")

        # ── 5. 生成 FoodNutritionEntry ───────────────────────────────────
        print("生成 FoodNutritionEntry 数据...")
        food_nutritions = []
        for food_id in food_ids:
            # 每个食品随机关联 8~20 个营养项
            import random
            random.seed(food_id + 1000)
            chosen = random.sample(nutrition_ids, k=random.randint(8, min(20, len(nutrition_ids))))
            for nut_id in chosen:
                food_nutritions.append(make_food_nutrition(food_id, nut_id))
        session.add_all(food_nutritions)
        await session.flush()
        print(f"  完成：{len(food_nutritions)} 条 FoodNutritionEntry")

        # ── 6. 生成 AnalysisDetail ────────────────────────────────────────
        print("生成 AnalysisDetail 数据...")
        analyses = []
        # 每个食品生成 8~15 条分析
        for food_id in food_ids:
            import random
            random.seed(food_id + 2000)
            for _ in range(random.randint(8, 15)):
                analyses.append(make_analysis_detail(food_id, "food", food_id))
        # 每个配料生成 3 条分析，其中 1 条必须是 ingredient_summary
        for ing_id in ingredient_ids:
            import random
            random.seed(ing_id + 3000)
            # 第1条：ingredient_summary（保证有评级）
            analyses.append(make_analysis_detail(ing_id, "ingredient", ing_id, "ingredient_summary"))
            # 第2条和第3条：随机类型
            analyses.append(make_analysis_detail(ing_id, "ingredient", ing_id))
            analyses.append(make_analysis_detail(ing_id, "ingredient", ing_id))
        session.add_all(analyses)
        print(f"  完成：{len(analyses)} 条 AnalysisDetail")

        await session.commit()

    print("\n✅ 数据插入完成！")
    print(f"   Foods:              {food_count}")
    print(f"   Ingredients:         {ingredient_count}")
    print(f"   NutritionTable:     {nutrition_count}")
    print(f"   FoodIngredients:    {len(food_ingredients)}")
    print(f"   FoodNutritionEntry: {len(food_nutritions)}")
    print(f"   AnalysisDetail:     {len(analyses)}")


if __name__ == "__main__":
    asyncio.run(seed())
