"""
SessionStore 单元测试：内存 session 管理，LRU + TTL + asyncio.Lock。
"""
import asyncio

import pytest

from app.core.agent.session_store import SessionStore


@pytest.fixture
def store():
    return SessionStore(max_size=3, ttl_seconds=3600)


@pytest.mark.asyncio
async def test_get_or_create_creates_new_session(store):
    """不存在的 session_id 应创建新 session"""
    session = await store.get_or_create("abc")
    assert session is not None


@pytest.mark.asyncio
async def test_get_or_create_returns_same_session(store):
    """同一 session_id 返回同一对象"""
    s1 = await store.get_or_create("abc")
    s2 = await store.get_or_create("abc")
    assert s1 is s2


@pytest.mark.asyncio
async def test_get_or_create_unknown_id_creates_new(store):
    """未知 session_id（如重启后）静默创建新 session，不报错"""
    session = await store.get_or_create("nonexistent-id-after-restart")
    assert session is not None


@pytest.mark.asyncio
async def test_max_size_evicts_oldest(store):
    """超过 max_size 时，最旧的 session 被驱逐"""
    s1 = await store.get_or_create("id1")
    s2 = await store.get_or_create("id2")
    s3 = await store.get_or_create("id3")
    # 添加第 4 个，应驱逐 id1
    s4 = await store.get_or_create("id4")
    # id1 再次访问时，应创建新 session（不是原来的对象）
    s1_new = await store.get_or_create("id1")
    assert s1_new is not s1


@pytest.mark.asyncio
async def test_concurrent_access_same_id(store):
    """并发访问同一 session_id 不产生竞态条件"""
    results = await asyncio.gather(*[store.get_or_create("shared") for _ in range(10)])
    # 所有结果应是同一个对象
    assert all(r is results[0] for r in results)