"""Redis 任务状态机 — 封装分析任务的读写操作。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from config import settings
from workflow_product_analysis.types import AnalysisError, AnalysisStatus, AnalysisTask, ProductAnalysisResult

_REDIS_KEY_PREFIX = "analysis"


def _task_key(task_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:{task_id}"


async def create_task(redis: Redis, task_id: str) -> AnalysisTask:
    """在 Redis 中写入初始任务记录（status="ocr"）。不设 TTL，终态时由 set_task_done/failed 设置。"""
    task: AnalysisTask = {
        "task_id": task_id,
        "status": "ocr",
        "error": None,
        "result": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "image_object_key": None,
    }
    await redis.set(_task_key(task_id), json.dumps(task))
    return task


async def get_task(redis: Redis, task_id: str) -> AnalysisTask | None:
    """读取任务记录。key 不存在返回 None。"""
    raw = await redis.get(_task_key(task_id))
    if raw is None:
        return None
    return json.loads(raw)


async def update_task_status(redis: Redis, task_id: str, status: AnalysisStatus) -> None:
    """仅更新 status 字段，其余字段不变。"""
    task = await get_task(redis, task_id)
    if task is None:
        return
    task["status"] = status
    await redis.set(_task_key(task_id), json.dumps(task))


async def set_task_done(
    redis: Redis,
    task_id: str,
    result: ProductAnalysisResult,
    ttl: int,
) -> None:
    """将 status 置为 "done"，写入 result，设置 TTL（秒）。"""
    task = await get_task(redis, task_id)
    if task is None:
        return
    task["status"] = "done"
    task["result"] = result
    await redis.set(_task_key(task_id), json.dumps(task), ex=ttl)


async def set_task_failed(
    redis: Redis,
    task_id: str,
    error: AnalysisError,
    ttl: int,
) -> None:
    """将 status 置为 "failed"，写入 error，设置 TTL（秒）。"""
    task = await get_task(redis, task_id)
    if task is None:
        return
    task["status"] = "failed"
    task["error"] = error
    await redis.set(_task_key(task_id), json.dumps(task), ex=ttl)


async def get_redis_client() -> Redis:
    """返回 Redis 异步客户端（从 settings.REDIS_URL 读取）。作为 FastAPI dependency 使用。"""
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)
