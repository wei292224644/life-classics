from unittest.mock import AsyncMock, patch, MagicMock
import pytest


async def test_embed_batch_returns_vectors():
    """embed_batch 返回与输入等长的向量列表"""
    mock_model = MagicMock()
    mock_model.aembed_documents = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])

    with patch("kb.embeddings._create_embedding_model", return_value=mock_model):
        from kb.embeddings import embed_batch
        result = await embed_batch(["文本一", "文本二"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2]
    mock_model.aembed_documents.assert_called_once_with(["文本一", "文本二"])


def test_create_embedding_model_uses_ollama():
    """Embedding provider 为 ollama 时使用 OllamaEmbeddings"""
    with patch("kb.embeddings.settings") as mock_settings, \
         patch("kb.embeddings.OllamaEmbeddings") as mock_cls:
        mock_settings.EMBEDDING_LLM_PROVIDER = "ollama"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"

        from kb.embeddings import _create_embedding_model
        _create_embedding_model()

        mock_cls.assert_called_once_with(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )
