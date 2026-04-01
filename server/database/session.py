"""
SQLAlchemy 异步 Session 工厂与 FastAPI 依赖注入。
"""

from collections.abc import AsyncGenerator

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings


def _build_url() -> str:
    """
    优先使用 POSTGRES_URL 直连字符串；
    若为空，则从分项配置拼装。
    """
    if settings.POSTGRES_URL:
        return settings.POSTGRES_URL
    return (
        f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


_engine = create_async_engine(_build_url(), pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：提供一次请求作用域的异步 Session。"""
    async with _session_factory() as session:
        yield session


@asynccontextmanager
async def get_async_session_cm():
    """异步上下文管理器版本，用于非 Depends() 场景下的 async with。"""
    async with _session_factory() as session:
        yield session
