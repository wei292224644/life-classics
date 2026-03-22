"""插入测试食品数据"""
import asyncio
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Food, Ingredient, FoodIngredient, NutritionTable, FoodNutritionEntry

POSTGRES_URL = "postgresql+psycopg://admin:123456@localhost:5432/life-classics"


async def main():
    engine = create_async_engine(POSTGRES_URL, pool_pre_ping=True)

    async with engine.begin() as conn:
        # 检查是否已有数据
        result = await conn.execute(text("SELECT COUNT(*) FROM foods"))
        count = result.scalar()
        if count > 0:
            print(f"数据库已有 {count} 条食品记录，跳过插入")
            return

        # 插入食品
        result = await conn.execute(
            text("""
                INSERT INTO foods (barcode, name, manufacturer, origin_place, shelf_life, net_content, image_url_list)
                VALUES (:barcode, :name, :manufacturer, :origin_place, :shelf_life, :net_content, :image_url_list)
                RETURNING id
            """),
            {
                "barcode": "6901234567890",
                "name": "测试饼干",
                "manufacturer": "测试食品有限公司",
                "origin_place": "中国",
                "shelf_life": "12个月",
                "net_content": "100g",
                "image_url_list": [],
            }
        )
        food_id = result.scalar()
        print(f"插入食品 ID: {food_id}")

        # 插入配料
        result = await conn.execute(
            text("""
                INSERT INTO ingredients (name, alias, is_additive, who_level, allergen_info, function_type)
                VALUES (:name, :alias, :is_additive, :who_level, :allergen_info, :function_type)
                RETURNING id
            """),
            {
                "name": "小麦粉",
                "alias": ["面粉"],
                "is_additive": False,
                "who_level": "Unknown",
                "allergen_info": "含麸质",
                "function_type": None,
            }
        )
        ing_id = result.scalar()
        print(f"插入配料 ID: {ing_id}")

        # 插入食品-配料关联
        await conn.execute(
            text("""
                INSERT INTO food_ingredients (food_id, ingredient_id, order_index)
                VALUES (:food_id, :ingredient_id, :order_index)
            """),
            {"food_id": food_id, "ingredient_id": ing_id, "order_index": 1}
        )

        # 插入营养成分类型
        result = await conn.execute(
            text("""
                INSERT INTO nutrition_table (name, alias, daily_value, daily_value_unit)
                VALUES (:name, :alias, :daily_value, :daily_value_unit)
                RETURNING id
            """),
            {
                "name": "能量",
                "alias": [],
                "daily_value": Decimal("2000.00"),
                "daily_value_unit": "kJ",
            }
        )
        nut_id = result.scalar()
        print(f"插入营养成分 ID: {nut_id}")

        # 插入食品营养值
        await conn.execute(
            text("""
                INSERT INTO food_nutrition_table (food_id, nutrition_id, value, value_unit, reference_type, reference_unit)
                VALUES (:food_id, :nutrition_id, :value, :value_unit, :reference_type, :reference_unit)
            """),
            {
                "food_id": food_id,
                "nutrition_id": nut_id,
                "value": "2000.0000",
                "value_unit": "kJ",
                "reference_type": "PER_100_WEIGHT",
                "reference_unit": "g",
            }
        )

        print("测试数据插入完成!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
