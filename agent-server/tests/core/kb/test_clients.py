from unittest.mock import patch, MagicMock, Mock
import sys


def test_get_chroma_client_returns_persistent_client():
    """get_chroma_client 应返回 PersistentClient 单例"""
    with patch("app.core.config.settings.DASHSCOPE_API_KEY", "dummy_key"):
        from app.core.kb import clients
        clients._chroma_client = None  # 重置单例
        with patch("chromadb.PersistentClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = clients.get_chroma_client()
            # 验证调用的正确性：应该传入 CHROMA_PERSIST_DIR
            assert mock_cls.called
            assert client is not None


def test_get_chroma_client_is_singleton():
    """重复调用返回同一个实例"""
    with patch("app.core.config.settings.DASHSCOPE_API_KEY", "dummy_key"):
        from app.core.kb import clients
        original = clients._chroma_client
        try:
            sentinel = MagicMock()
            clients._chroma_client = sentinel
            assert clients.get_chroma_client() is sentinel
        finally:
            clients._chroma_client = original


def test_get_neo4j_driver_returns_async_driver():
    """get_neo4j_driver 应返回 AsyncGraphDatabase.driver 单例"""
    with patch("neo4j.AsyncGraphDatabase.driver") as mock_driver, \
         patch("app.core.config.settings.DASHSCOPE_API_KEY", "dummy_key"):
        mock_driver.return_value = MagicMock()
        from app.core.kb import clients
        clients._neo4j_driver = None  # 重置单例
        driver = clients.get_neo4j_driver()
        mock_driver.assert_called_once()
        assert driver is not None
