"""
Ollama 提供者实现
"""

from typing import Any, Optional
import warnings

from app.core.providers.base import BaseLLMProvider, BaseEmbeddingProvider


class OllamaLLMProvider(BaseLLMProvider):
    """Ollama LLM 提供者"""

    def validate_config(self) -> bool:
        """验证 Ollama 配置"""
        # Ollama 不需要 API Key，只需要 base_url 和 model
        return True

    def create_instance(self) -> Any:
        """创建 Ollama LLM 实例"""
        try:
            from llama_index.llms.ollama import Ollama
        except ImportError:
            raise ImportError(
                "Ollama LLM不可用，请安装: pip install llama-index-llms-ollama"
            )

        return Ollama(
            model=self.config.get("model", "llama2"),
            base_url=self.config.get("base_url", "http://localhost:11434"),
            temperature=self.config.get("temperature", 0.7),
            request_timeout=self.config.get("request_timeout", 120.0),
        )


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama Embedding 提供者"""

    def validate_config(self) -> bool:
        """验证 Ollama Embedding 配置"""
        # Ollama 不需要 API Key
        return True

    def create_instance(self) -> Any:
        """创建 Ollama Embedding 实例"""
        try:
            from llama_index.embeddings.ollama import OllamaEmbedding
        except ImportError:
            raise ImportError(
                "OllamaEmbedding 不可用，请安装: pip install llama-index-embeddings-ollama"
            )

        return OllamaEmbedding(
            model_name=self.config.get("model", "qwen3-embedding:4b"),
            base_url=self.config.get("base_url", "http://localhost:11434"),
        )
