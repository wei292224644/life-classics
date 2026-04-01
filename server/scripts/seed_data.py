"""
Seed 脚本：向 PostgreSQL 插入大量假数据，供前端联调使用。

用法：
    cd server
    uv run python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import os
import random
import sys
import uuid
from datetime import datetime

_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from faker import Faker
fake = Faker("zh_CN")
Faker.seed(42)

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import _session_factory
from database.models import (
    Food,
    Ingredient,
    FoodIngredient,
    NutritionTable,
    FoodNutritionEntry,
    IarcAgent,
    IarcCancerSite,
    IarcAgentLink,
    IngredientAlias,
)


SYSTEM_USER = uuid.UUID("00000000-0000-0000-0000-000000000000")


# ── 数据生成函数 ────────────────────────────────────────────────────────────

def make_food(index: int) -> Food:
    categories = ["零食", "饮料", "调味品", "乳制品", "肉制品", "糕点", "糖果", "方便食品", "坚果炒货", "酒类"]
    manufacturers = ["伊利实业集团有限公司", "蒙牛乳业（集团）股份有限公司", "康师傅控股有限公司", "统一企业（中国）投资有限公司", "娃哈哈集团有限公司", "农夫山泉股份有限公司", "可口可乐饮料（上海）有限公司", "百事可乐（中国）有限公司", "亿滋（中国）有限公司", "上海太太乐食品有限公司", "李锦记（广州）食品有限公司", "海底捞调味品有限公司"]
    return Food(
        barcode=f"69{str(index + 1).zfill(10)}",
        name=fake.catch_phrase() + " " + fake.random_element(elements=["礼盒装", "家庭装", "迷你装", "量贩装", ""]),
        image_url_list=[f"https://picsum.photos/seed/{index}/400/400", f"https://picsum.photos/seed/{index + 1000}/400/400"],
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
    additive_codes = [None, "F202", "E330", "E951", "E500", "E452", "E300", "E322"]
    who_levels = ["Group 1", "Group 2A", "Group 2B", "Group 3", "Group 4"]
    function_types = ["防腐剂", "增稠剂", "乳化剂", "抗氧化剂", "着色剂", "甜味剂", "酸度调节剂", "香料", "营养强化剂", "稳定剂"]
    allergen_infos = ["含有麸质", "含有乳糖", "含有大豆", "含有花生", "含有甲壳类", "含有鱼类", "含有蛋类", "含有坚果"]
    origin_types = ["天然", "合成", "半合成"]
    descriptions = ["这是一种广泛使用的食品配料，具有增香、防腐或改善口感的作用。", "天然提取物，来自植物或动物来源，经过精制加工而成。", "人工合成添加剂，在合法范围内使用安全性已得到验证。", "常见的食品添加剂之一，主要用于改善食品的色泽、口感和保质期。", "营养强化剂，可补充食品中的特定营养成分，满足人体健康需求。"]
    is_additive = fake.boolean(chance_of_getting_true=60)
    return Ingredient(
        name=fake.unique.first_name() + fake.random_element(["酸", "酯", "醇", "盐", "糖", "素"]),
        alias=[fake.name(), fake.name()] if fake.boolean() else [],
        description=fake.random_element(descriptions),
        is_additive=is_additive,
        additive_code=fake.random_element(additive_codes) if is_additive else None,
        standard_code=f"GB {fake.random_int(min=1000, max=9999)}" if fake.boolean() else None,
        who_level=fake.random_element(who_levels),
        allergen_info=fake.random_elements(allergen_infos, length=fake.random_int(0, 3), unique=True),
        function_type=fake.random_elements(function_types, length=fake.random_int(1, 3), unique=True),
        origin_type=fake.random_element(origin_types) if fake.boolean() else None,
        limit_usage=f"{fake.random_int(1, 100)}mg/kg" if fake.boolean() else None,
        legal_region=fake.random_element(["中国", "欧盟", "美国", "日本", "Codex"]),
        cas=f"{fake.random_int(min=100, max=999)}-{fake.random_int(min=10, max=99)}-{fake.random_int(min=1, max=9)}" if fake.boolean() else None,
        applications=fake.sentence(nb_words=8) if fake.boolean() else None,
        notes=fake.sentence(nb_words=12) if fake.boolean() else None,
        safety_info=fake.text(max_nb_chars=100) if fake.boolean() else None,
        meta={},
    )


def make_nutrition(index: int) -> NutritionTable:
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
        meta={},
        created_by_user=SYSTEM_USER,
    )


def make_food_ingredient(food_id: int, ingredient_id: int) -> FoodIngredient:
    return FoodIngredient(
        food_id=food_id,
        ingredient_id=ingredient_id,
        created_by_user=SYSTEM_USER,
    )


def make_food_nutrition(food_id: int, nutrition_id: int) -> FoodNutritionEntry:
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


def make_ingredient_alias(ingredient_id: int, index: int) -> IngredientAlias:
    """生成一条 IngredientAlias 记录"""
    alias_types = ["chinese", "english", "abbr"]
    alias_name = fake.unique.name()
    return IngredientAlias(
        ingredient_id=ingredient_id,
        alias=alias_name,
        normalized_alias=alias_name,
        alias_type=fake.random_element(alias_types),
    )


# IARC 相关

def make_iarc_agent(index: int) -> IarcAgent:
    """生成一条 IarcAgent 记录"""
    groups = ["1", "2A", "2B", "3", "unknown"]
    agent_names = [
        "Benzene", "Formaldehyde", "Ethylene oxide", "Asbestos", "Silica dust",
        "Solar radiation", "Tobacco smoke", "Alcoholic beverages", "Processed meat",
        "Salt (sodium chloride)", "Beta-carotene supplements", "Fried foods",
    ]
    zh_names = [
        "苯", "甲醛", "环氧乙烷", "石棉", "硅尘",
        "太阳辐射", "烟草烟雾", "酒精饮料", "加工肉制品",
        "盐（氯化钠）", "β-胡萝卜素补充剂", "油炸食品",
    ]
    return IarcAgent(
        cas_no=f"{fake.random_int(min=10000, max=99999)}-{fake.random_int(min=10, max=99)}-{fake.random_int(min=1, max=9)}",
        agent_name=fake.random_element(agent_names) if index >= len(agent_names) else agent_names[index % len(agent_names)],
        zh_agent_name=fake.random_element(zh_names) if index >= len(zh_names) else zh_names[index % len(zh_names)],
        group=fake.random_element(groups),
        volume=f"Volume {fake.random_int(min=1, max=130)}",
        volume_publication_year=str(fake.random_int(min=1970, max=2024)),
        evaluation_year=str(fake.random_int(min=1970, max=2024)),
        additional_information=fake.text(max_nb_chars=100) if fake.boolean() else None,
        created_by_user=SYSTEM_USER,
    )


def make_iarc_cancer_site(index: int, agent_ids: list[int]) -> IarcCancerSite:
    """生成一条 IarcCancerSite 记录"""
    sites = [
        ("Lung", "肺"),
        ("Liver", "肝"),
        ("Breast", "乳腺"),
        ("Colorectum", "结直肠"),
        ("Stomach", "胃"),
    ]
    name, zh_name = sites[index % len(sites)]
    random.seed(index)
    sufficient = random.sample(agent_ids, k=random.randint(0, min(3, len(agent_ids)))) if agent_ids else []
    limited = random.sample(agent_ids, k=random.randint(0, min(2, len(agent_ids)))) if agent_ids else []
    return IarcCancerSite(
        name=name,
        zh_name=zh_name,
        description=fake.sentence(nb_words=10) if fake.boolean() else None,
        sufficient_evidence_agents=sufficient,
        limited_evidence_agents=limited,
        created_by_user=SYSTEM_USER,
    )


def make_iarc_agent_link(from_id: int, to_id: int, index: int) -> IarcAgentLink:
    """生成一条 IarcAgentLink 记录"""
    link_types = ["see", "see_also"]
    return IarcAgentLink(
        from_agent_id=from_id,
        to_agent_id=to_id,
        link_type=link_types[index % len(link_types)],
        created_by_user=SYSTEM_USER,
    )


# ── 主函数 ──────────────────────────────────────────────────────────────────

async def _clear_tables(session: AsyncSession) -> None:
    """按外键依赖顺序清空所有相关表"""
    print("正在清空旧数据...")
    await session.execute(delete(FoodNutritionEntry))
    await session.execute(delete(FoodIngredient))
    await session.execute(delete(Food))
    await session.execute(delete(Ingredient))
    await session.execute(delete(NutritionTable))
    await session.execute(delete(IngredientAlias))
    await session.execute(delete(IarcAgentLink))
    await session.execute(delete(IarcCancerSite))
    await session.execute(delete(IarcAgent))
    await session.commit()
    print("清空完成。")


async def seed():
    """生成并插入所有假数据"""
    async with _session_factory() as session:
        await _clear_tables(session)

        # 1. Ingredient
        print("生成 Ingredient 数据...")
        ingredient_count = 80
        ingredients = [make_ingredient(i) for i in range(ingredient_count)]
        session.add_all(ingredients)
        await session.flush()
        ingredient_ids = [ing.id for ing in ingredients]
        print(f"  完成：{ingredient_count} 条 Ingredient")

        # 2. NutritionTable
        print("生成 NutritionTable 数据...")
        nutrition_count = 15
        nutritions = [make_nutrition(i) for i in range(nutrition_count)]
        session.add_all(nutritions)
        await session.flush()
        nutrition_ids = [n.id for n in nutritions]
        print(f"  完成：{nutrition_count} 条 NutritionTable")

        # 3. Food
        print("生成 Food 数据...")
        food_count = 50
        foods = [make_food(i) for i in range(food_count)]
        session.add_all(foods)
        await session.flush()
        food_ids = [f.id for f in foods]
        print(f"  完成：{food_count} 条 Food")

        # 4. FoodIngredient
        print("生成 FoodIngredient 关联数据...")
        food_ingredients = []
        for food_id in food_ids:
            random.seed(food_id)
            chosen = random.sample(ingredient_ids, k=random.randint(5, min(15, len(ingredient_ids))))
            for ing_id in chosen:
                food_ingredients.append(make_food_ingredient(food_id, ing_id))
        session.add_all(food_ingredients)
        await session.flush()
        print(f"  完成：{len(food_ingredients)} 条 FoodIngredient")

        # 5. FoodNutritionEntry
        print("生成 FoodNutritionEntry 数据...")
        food_nutritions = []
        for food_id in food_ids:
            random.seed(food_id + 1000)
            chosen = random.sample(nutrition_ids, k=random.randint(8, min(20, len(nutrition_ids))))
            for nut_id in chosen:
                food_nutritions.append(make_food_nutrition(food_id, nut_id))
        session.add_all(food_nutritions)
        await session.flush()
        print(f"  完成：{len(food_nutritions)} 条 FoodNutritionEntry")

        # 6. IngredientAlias
        print("生成 IngredientAlias 数据...")
        aliases = []
        for ing_id in ingredient_ids:
            random.seed(ing_id + 5000)
            alias_count = random.randint(0, 3)
            for j in range(alias_count):
                aliases.append(make_ingredient_alias(ing_id, ing_id * 10 + j))
        session.add_all(aliases)
        await session.flush()
        print(f"  完成：{len(aliases)} 条 IngredientAlias")

        # 7. IarcAgent
        print("生成 IarcAgent 数据...")
        iarc_agent_count = 10
        iarc_agents = [make_iarc_agent(i) for i in range(iarc_agent_count)]
        session.add_all(iarc_agents)
        await session.flush()
        agent_ids = [a.id for a in iarc_agents]
        print(f"  完成：{iarc_agent_count} 条 IarcAgent")

        # 8. IarcCancerSite
        print("生成 IarcCancerSite 数据...")
        iarc_site_count = 5
        iarc_sites = [make_iarc_cancer_site(i, agent_ids) for i in range(iarc_site_count)]
        session.add_all(iarc_sites)
        await session.flush()
        print(f"  完成：{iarc_site_count} 条 IarcCancerSite")

        # 9. IarcAgentLink
        print("生成 IarcAgentLink 数据...")
        iarc_links = []
        for i, from_id in enumerate(agent_ids):
            random.seed(from_id + 7000)
            link_count = random.randint(0, 2)
            possible_targets = [a for a in agent_ids if a != from_id]
            for j in range(link_count):
                if possible_targets:
                    to_id = random.choice(possible_targets)
                    iarc_links.append(make_iarc_agent_link(from_id, to_id, i * 10 + j))
        session.add_all(iarc_links)
        print(f"  完成：{len(iarc_links)} 条 IarcAgentLink")

        await session.commit()

    print("\n✅ 数据插入完成！")
    print(f"   Foods:              {food_count}")
    print(f"   Ingredients:         {ingredient_count}")
    print(f"   NutritionTable:     {nutrition_count}")
    print(f"   FoodIngredients:    {len(food_ingredients)}")
    print(f"   FoodNutritionEntry: {len(food_nutritions)}")
    print(f"   IngredientAlias:     {len(aliases)}")
    print(f"   IarcAgent:          {iarc_agent_count}")
    print(f"   IarcCancerSite:     {iarc_site_count}")
    print(f"   IarcAgentLink:      {len(iarc_links)}")


if __name__ == "__main__":
    asyncio.run(seed())
