"""
OpenRouter 提供者实现
OpenRouter 是一个统一的 API 网关，支持多种模型
"""

from typing import Any, Optional
import warnings

from app.core.providers.base import BaseLLMProvider, BaseEmbeddingProvider


class OpenRouterLLMProvider(BaseLLMProvider):
    """OpenRouter LLM 提供者"""

    def validate_config(self) -> bool:
        """验证 OpenRouter 配置"""
        if not self.config.get("api_key"):
            raise ValueError("OPENROUTER_API_KEY 未设置，请在.env文件中配置")
        return True

    def create_instance(self) -> Any:
        """创建 OpenRouter LLM 实例"""
        try:
            from llama_index.llms.openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI LLM不可用，请安装: pip install llama-index-llms-openai"
            )

        self.validate_config()

        # OpenRouter 兼容 OpenAI API，使用 OpenAI 客户端
        return OpenAI(
            model=self.config.get("model", "openai/gpt-3.5-turbo"),
            api_key=self.config["api_key"],
            api_base="https://openrouter.ai/api/v1",
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 2048),
        )


class OpenRouterEmbeddingProvider(BaseEmbeddingProvider):
    """OpenRouter Embedding 提供者"""

    def validate_config(self) -> bool:
        """验证 OpenRouter Embedding 配置"""
        if not self.config.get("api_key"):
            raise ValueError("OPENROUTER_API_KEY 未设置，请在.env文件中配置")
        return True

    def create_instance(self) -> Any:
        """创建 OpenRouter Embedding 实例"""
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding
        except ImportError:
            raise ImportError(
                "OpenAIEmbedding 不可用，请安装: pip install llama-index-embeddings-openai"
            )

        self.validate_config()

        # OpenRouter 兼容 OpenAI API
        return OpenAIEmbedding(
            model=self.config.get("model", "text-embedding-ada-002"),
            api_key=self.config["api_key"],
            api_base="https://openrouter.ai/api/v1",
        )
