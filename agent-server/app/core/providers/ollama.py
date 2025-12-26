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
        from langchain_ollama import ChatOllama

        # 基础参数（ChatOllama 直接支持的参数，带默认值）
        default_params = {
            "model": "llama2",
            "base_url": "http://localhost:11434",
            "temperature": 0.7,
        }

        # 合并参数：先使用默认值，然后用 config 中的值覆盖
        merged_params = default_params.copy()

        for key, value in self.config.items():
            merged_params[key] = value

        return ChatOllama(**merged_params)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama Embedding 提供者"""

    def validate_config(self) -> bool:
        """验证 Ollama Embedding 配置"""
        # Ollama 不需要 API Key
        return True

    def create_instance(self) -> Any:
        """创建 Ollama Embedding 实例"""
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=self.config.get("model", "qwen3-embedding:4b"),
            base_url=self.config.get("base_url", "http://localhost:11434"),
        )
