"""
数据库重置脚本：根据 models.py 自动同步表结构

使用方式：
  # 仅创建数据库（如不存在）和所有表
  uv run python3 reset_db.py

  # 重建所有表（删除并重新创建）
  uv run python3 reset_db.py --rebuild
"""
import argparse
import asyncio
import sys
import os

# Add the parent directory (server) to sys.path so that 'database' module can be found
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from database.base import Base
from database.models import (
    Food, Ingredient, FoodIngredient, NutritionTable,
    FoodNutritionEntry, AnalysisDetail,
    IarcAgent, IarcCancerSite, IarcAgentLink,
)

# 所有枚举类型定义（名称 -> 值列表）
ENUM_TYPES = {
    "who_level": ["Group 1", "Group 2A", "Group 2B", "Group 3", "Group 4", "Unknown"],
    "reference_unit": ["g", "mg", "kcal", "mL", "kJ", "serving", "day"],
    "unit": ["g", "mg", "kcal", "mL", "kJ"],
    "reference_type": ["PER_100_WEIGHT", "PER_100_ENERGY", "PER_SERVING", "PER_DAY"],
    "analysis_target": ["food", "ingredient"],
    "analysis_type": ["usage_advice_summary", "health_summary", "pregnancy_safety", "risk_summary", "recent_risk_summary", "ingredient_summary", "overall_risk"],
    "analysis_version": ["v1"],
    "level": ["t4", "t3", "t2", "t1", "t0", "unknown"],
    "iarc_agent_group": ["1", "2A", "2B", "3", "unknown"],
    "iarc_agent_link_type": ["see", "see_also"],
}


def get_postgres_url(with_db: bool = True) -> str:
    user = "admin"
    password = "123456"
    host = "localhost"
    port = 5432
    db = "life-classics" if with_db else "postgres"
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


async def ensure_database() -> None:
    """确保 life-classics 数据库存在"""
    engine = create_async_engine(get_postgres_url(with_db=False), isolation_level="AUTOCOMMIT")
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'life-classics'")
        )
        if result.scalar() is None:
            await conn.execute(text("CREATE DATABASE life-classics OWNER admin"))
            print("数据库 life-classics 创建成功")
        else:
            print("数据库 life-classics 已存在")
    await engine.dispose()


async def create_enum_types() -> None:
    """创建所有枚举类型（如果不存在）"""
    engine = create_async_engine(get_postgres_url())
    async with engine.begin() as conn:
        for enum_name, values in ENUM_TYPES.items():
            # 检查类型是否已存在
            result = await conn.execute(
                text("SELECT 1 FROM pg_type WHERE typname = :enum_name"),
                {"enum_name": enum_name}
            )
            if result.scalar() is None:
                values_str = ", ".join(f"'{v}'" for v in values)
                await conn.execute(text(f"CREATE TYPE {enum_name} AS ENUM ({values_str})"))
                print(f"枚举类型 {enum_name} 创建成功")
            else:
                print(f"枚举类型 {enum_name} 已存在")
    await engine.dispose()


async def drop_enum_types() -> None:
    """删除所有枚举类型"""
    engine = create_async_engine(get_postgres_url())
    async with engine.begin() as conn:
        for enum_name in ENUM_TYPES.keys():
            result = await conn.execute(
                text("SELECT 1 FROM pg_type WHERE typname = :enum_name"),
                {"enum_name": enum_name}
            )
            if result.scalar() is not None:
                await conn.execute(text(f"DROP TYPE {enum_name}"))
                print(f"枚举类型 {enum_name} 已删除")
    await engine.dispose()


async def create_tables() -> None:
    """根据 models 创建所有表"""
    engine = create_async_engine(get_postgres_url())
    async with engine.begin() as conn:
        # 导入所有 model 以确保它们被注册到 Base.metadata
        for model in [Food, Ingredient, FoodIngredient, NutritionTable, FoodNutritionEntry, AnalysisDetail]:
            pass
        await conn.run_sync(Base.metadata.create_all)
        print("所有表创建成功")
    await engine.dispose()


async def drop_tables() -> None:
    """删除所有表"""
    engine = create_async_engine(get_postgres_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("所有表已删除")
    await engine.dispose()


async def main(rebuild: bool) -> None:
    await ensure_database()
    if rebuild:
        await drop_tables()
        await drop_enum_types()
    await create_enum_types()
    await create_tables()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="重置数据库表结构")
    worflow_parser_kb.add_argument("--rebuild", action="store_true", help="删除并重建所有表")
    args = worflow_parser_kb.parse_args()
    asyncio.run(main(args.rebuild))
