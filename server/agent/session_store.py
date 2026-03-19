"""
SessionStore：基于内存的 Agno session 存储，使用 cachetools + asyncio.Lock。
"""
import asyncio
import uuid
from typing import Any, Optional

from cachetools import TTLCache


class SessionStore:
    """
    管理 Agno Agent 的 session 对象。

    - 最多 max_size 个 session（LRU 驱逐）
    - ttl_seconds 内无访问的 session 自动清除
    - asyncio.Lock 保证并发安全
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 86400):
        self._cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: Optional[str] = None) -> Any:
        """
        获取已有 session 或创建新 session。

        Args:
            session_id: 客户端传入的 session ID；为 None 时自动生成

        Returns:
            session 对象（dict，供 Agno Agent 使用）
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        async with self._lock:
            if session_id not in self._cache:
                self._cache[session_id] = {"session_id": session_id, "history": []}
            return self._cache[session_id]

    async def clear(self, session_id: str) -> None:
        """清除指定 session"""
        async with self._lock:
            self._cache.pop(session_id, None)


# 全局单例
_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """获取全局 SessionStore 单例"""
    global _store
    if _store is None:
        _store = SessionStore()
    return _store