"""
Neo4j 共享 driver 单例模块。

提供模块级懒初始化的 Neo4j driver 实例，供 neo4j_query、neo4j_vector_search 等工具共用。
"""

from neo4j import GraphDatabase

from config import settings

# 模块级单例，初始为 None，首次调用 get_driver() 时创建
_driver = None


def get_driver():
    """
    返回全局共享的 Neo4j driver 单例。

    首次调用时使用配置中的 URI / 用户名 / 密码创建 driver，后续调用直接返回已有实例。

    Returns:
        neo4j.Driver: 共享的 Neo4j driver 实例
    """
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            connection_timeout=30,
        )
    return _driver


def get_database() -> str:
    """
    返回目标 Neo4j database 名称。

    Returns:
        str: settings.NEO4J_DATABASE 的值
    """
    return settings.NEO4J_DATABASE
