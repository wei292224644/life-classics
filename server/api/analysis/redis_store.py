"""Redis client factory for analysis module."""
from __future__ import annotations

from redis.asyncio import Redis

from config import settings


async def get_redis_client() -> Redis:
    """返回 Redis 异步客户端（从 settings.REDIS_URL 读取）。作为 FastAPI dependency 使用。"""
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)
