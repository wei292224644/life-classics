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
        from langchain_community.llms import Tongyi

        self.validate_config()

        return Tongyi(
            model_name=self.config.get("model", "qwen-max"),
            dashscope_api_key=self.config["api_key"],
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
        from langchain_community.embeddings import DashScopeEmbeddings

        self.validate_config()

        return DashScopeEmbeddings(
            model=self.config.get("model", "text-embedding-v2"),
            dashscope_api_key=self.config["api_key"],
        )
