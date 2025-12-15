"""
DashScope/Qwen 提供者实现
"""

from typing import Any, Optional
import warnings

from app.core.providers.base import BaseLLMProvider, BaseEmbeddingProvider


class DashScopeLLMProvider(BaseLLMProvider):
    """DashScope LLM 提供者"""

    def validate_config(self) -> bool:
        """验证 DashScope 配置"""
        if not self.config.get("api_key"):
            raise ValueError("DASHSCOPE_API_KEY 未设置，请在.env文件中配置")
        return True

    def create_instance(self) -> Any:
        """创建 DashScope LLM 实例"""
        try:
            from llama_index.llms.dashscope import DashScope
        except ImportError:
            raise ImportError(
                "DashScope LLM不可用，请安装: pip install llama-index-llms-dashscope"
            )

        self.validate_config()

        return DashScope(
            model=self.config.get("model", "qwen-max"),
            api_key=self.config["api_key"],
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 2048),
        )


class DashScopeEmbeddingProvider(BaseEmbeddingProvider):
    """DashScope Embedding 提供者"""

    def validate_config(self) -> bool:
        """验证 DashScope Embedding 配置"""
        if not self.config.get("api_key"):
            raise ValueError("DASHSCOPE_API_KEY 未设置，请在.env文件中配置")
        return True

    def create_instance(self) -> Any:
        """创建 DashScope Embedding 实例"""
        try:
            from llama_index.embeddings.dashscope import DashScopeEmbedding
        except ImportError:
            raise ImportError(
                "DashScopeEmbedding 不可用，请安装: pip install llama-index-embeddings-dashscope"
            )

        self.validate_config()

        return DashScopeEmbedding(
            model_name=self.config.get("model", "text-embedding-v2"),
            api_key=self.config["api_key"],
        )
