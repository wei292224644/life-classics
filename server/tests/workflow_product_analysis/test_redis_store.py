import json
import pytest
import fakeredis.aioredis as fakeredis

from workflow_product_analysis.redis_store import (
    create_task, get_task, update_task_status, set_task_done, set_task_failed,
)


@pytest.fixture
async def redis():
    r = await fakeredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


async def test_create_task_initial_structure(redis):
    task = await create_task(redis, "task-1")
    assert task["task_id"] == "task-1"
    assert task["status"] == "ocr"
    assert task["error"] is None
    assert task["result"] is None


async def test_get_task_not_found(redis):
    result = await get_task(redis, "nonexistent")
    assert result is None


async def test_get_task_found(redis):
    await create_task(redis, "task-2")
    task = await get_task(redis, "task-2")
    assert task is not None
    assert task["task_id"] == "task-2"


async def test_update_task_status_only_changes_status(redis):
    await create_task(redis, "task-3")
    await update_task_status(redis, "task-3", "parsing")
    task = await get_task(redis, "task-3")
    assert task["status"] == "parsing"
    assert task["error"] is None   # 其他字段不变
    assert task["result"] is None


async def test_set_task_done_writes_result_and_ttl(redis):
    await create_task(redis, "task-4")
    result = {"source": "agent_generated", "ingredients": [], "verdict": {"level": "t1", "description": "ok"},
               "advice": "fine", "alternatives": [], "demographics": [], "scenarios": [], "references": []}
    await set_task_done(redis, "task-4", result, ttl=3600)
    task = await get_task(redis, "task-4")
    assert task["status"] == "done"
    assert task["result"]["source"] == "agent_generated"
    # 验证 TTL 已设置
    ttl_val = await redis.ttl("analysis:task-4")
    assert ttl_val > 0


async def test_set_task_failed_writes_error_and_ttl(redis):
    await create_task(redis, "task-5")
    await set_task_failed(redis, "task-5", "ocr_failed", ttl=3600)
    task = await get_task(redis, "task-5")
    assert task["status"] == "failed"
    assert task["error"] == "ocr_failed"
    ttl_val = await redis.ttl("analysis:task-5")
    assert ttl_val > 0
