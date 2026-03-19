from __future__ import annotations

from typing import Any

import chromadb
from neo4j import AsyncDriver, AsyncGraphDatabase

from config import settings

_chroma_client: Any = None  # chromadb.api.ClientAPI，PersistentClient 是工厂函数非类
_neo4j_driver: AsyncDriver | None = None


def get_chroma_client():
    """返回 ChromaDB PersistentClient 单例（chromadb.api.ClientAPI）。"""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _chroma_client


def get_neo4j_driver() -> AsyncDriver:
    """返回 Neo4j 异步驱动单例。"""
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
        )
    return _neo4j_driver
