from unittest.mock import patch, MagicMock
import app.core.kb.clients as clients_module


def test_get_chroma_client_returns_persistent_client():
    """get_chroma_client 应返回 PersistentClient 单例"""
    original = clients_module._chroma_client
    try:
        clients_module._chroma_client = None
        with patch("chromadb.PersistentClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = clients_module.get_chroma_client()
            mock_cls.assert_called_once()
            assert client is not None
    finally:
        clients_module._chroma_client = original


def test_get_chroma_client_is_singleton():
    """重复调用返回同一个实例"""
    original = clients_module._chroma_client
    try:
        sentinel = MagicMock()
        clients_module._chroma_client = sentinel
        assert clients_module.get_chroma_client() is sentinel
    finally:
        clients_module._chroma_client = original


def test_get_neo4j_driver_returns_async_driver():
    """get_neo4j_driver 应返回 AsyncGraphDatabase.driver 单例"""
    original = clients_module._neo4j_driver
    try:
        clients_module._neo4j_driver = None
        with patch("neo4j.AsyncGraphDatabase.driver") as mock_driver:
            mock_driver.return_value = MagicMock()
            driver = clients_module.get_neo4j_driver()
            mock_driver.assert_called_once()
            assert driver is not None
    finally:
        clients_module._neo4j_driver = original


def test_get_neo4j_driver_is_singleton():
    """重复调用返回同一个实例"""
    original = clients_module._neo4j_driver
    try:
        sentinel = MagicMock()
        clients_module._neo4j_driver = sentinel
        assert clients_module.get_neo4j_driver() is sentinel
    finally:
        clients_module._neo4j_driver = original
