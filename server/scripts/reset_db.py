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
    await create_tables()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="重置数据库表结构")
    parser.add_argument("--rebuild", action="store_true", help="删除并重建所有表")
    args = parser.parse_args()
    asyncio.run(main(args.rebuild))
