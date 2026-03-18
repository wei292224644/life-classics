from unittest.mock import AsyncMock, patch, MagicMock
import pytest


async def test_embed_batch_returns_vectors():
    """embed_batch 返回与输入等长的向量列表"""
    mock_model = MagicMock()
    mock_model.aembed_documents = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])

    with patch("app.core.kb.embeddings._create_embedding_model", return_value=mock_model):
        from app.core.kb.embeddings import embed_batch
        result = await embed_batch(["文本一", "文本二"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2]
    mock_model.aembed_documents.assert_called_once_with(["文本一", "文本二"])


def test_create_embedding_model_uses_dashscope_credentials():
    """EMBEDDING_LLM_PROVIDER=dashscope 时使用 DashScope 凭证构建模型"""
    with patch("app.core.kb.embeddings.settings") as mock_settings, \
         patch("app.core.kb.embeddings.OpenAIEmbeddings") as mock_cls:
        mock_settings.EMBEDDING_LLM_PROVIDER = "dashscope"
        mock_settings.PARSER_LLM_PROVIDER = "openai"
        mock_settings.EMBEDDING_MODEL = "text-embedding-v3"
        mock_settings.DASHSCOPE_API_KEY = "ds-key"
        mock_settings.DASHSCOPE_BASE_URL = "https://dashscope.example.com/v1"

        from app.core.kb.embeddings import _create_embedding_model
        _create_embedding_model()

        mock_cls.assert_called_once_with(
            model="text-embedding-v3",
            api_key="ds-key",
            base_url="https://dashscope.example.com/v1",
            tiktoken_enabled=False,
        )


def test_create_embedding_model_fallback_to_parser_provider():
    """EMBEDDING_LLM_PROVIDER 为空时，fallback 到 PARSER_LLM_PROVIDER"""
    with patch("app.core.kb.embeddings.settings") as mock_settings, \
         patch("app.core.kb.embeddings.OpenAIEmbeddings") as mock_cls:
        mock_settings.EMBEDDING_LLM_PROVIDER = ""
        mock_settings.PARSER_LLM_PROVIDER = "dashscope"
        mock_settings.EMBEDDING_MODEL = "text-embedding-v3"
        mock_settings.DASHSCOPE_API_KEY = "ds-key"
        mock_settings.DASHSCOPE_BASE_URL = "https://dashscope.example.com/v1"

        from app.core.kb.embeddings import _create_embedding_model
        _create_embedding_model()

        mock_cls.assert_called_once_with(
            model="text-embedding-v3",
            api_key="ds-key",
            base_url="https://dashscope.example.com/v1",
            tiktoken_enabled=False,
        )


def test_create_embedding_model_uses_ollama_base_url():
    """EMBEDDING_LLM_PROVIDER=ollama 时使用 Ollama 的 OpenAI-compatible /v1 端点"""
    with patch("app.core.kb.embeddings.settings") as mock_settings, \
         patch("app.core.kb.embeddings.OpenAIEmbeddings") as mock_cls:
        mock_settings.EMBEDDING_LLM_PROVIDER = "ollama"
        mock_settings.PARSER_LLM_PROVIDER = "openai"
        mock_settings.EMBEDDING_MODEL = "qwen3-embedding:4b"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"

        from app.core.kb.embeddings import _create_embedding_model
        _create_embedding_model()

        mock_cls.assert_called_once_with(
            model="qwen3-embedding:4b",
            api_key="ollama",
            base_url="http://localhost:11434/v1",
            tiktoken_enabled=False,
        )
