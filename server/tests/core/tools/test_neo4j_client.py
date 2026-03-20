"""
tests/core/tools/test_neo4j_client.py

测试 neo4j_client 模块：共享 driver 单例与 database 名称获取。
"""

from unittest.mock import MagicMock, patch

import agent.tools.neo4j_client as neo4j_client_module
from config import settings


def test_get_driver_returns_singleton():
    """两次调用 get_driver() 应返回同一对象，且 driver 构造函数只被调用一次。"""
    # 重置单例状态，确保测试隔离
    neo4j_client_module._driver = None

    mock_driver_instance = MagicMock()

    with patch(
        "agent.tools.neo4j_client.GraphDatabase.driver",
        return_value=mock_driver_instance,
    ) as mock_constructor:
        driver1 = neo4j_client_module.get_driver()
        driver2 = neo4j_client_module.get_driver()

    assert driver1 is driver2, "两次调用应返回同一实例"
    mock_constructor.assert_called_once(), "driver 构造函数应只被调用一次"

    # 测试结束后重置，避免污染其他测试
    neo4j_client_module._driver = None


def test_get_database_returns_configured_value():
    """get_database() 应返回 settings.NEO4J_DATABASE 的值。"""
    result = neo4j_client_module.get_database()
    assert result == settings.NEO4J_DATABASE
