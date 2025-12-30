"""
DashScope/Qwen 提供者实现
"""

import os
from typing import Any, Optional
import warnings

from app.core.providers.base import (
    BaseLLMProvider,
    BaseEmbeddingProvider,
    BaseMultiModalConversationProvider,
)


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
        import dashscope

        self.validate_config()

        # 设置环境变量和 dashscope.api_key，确保 dashscope 库能够找到 API key
        api_key = self.config["api_key"]
        if api_key:
            os.environ["DASHSCOPE_API_KEY"] = api_key
            dashscope.api_key = api_key  # 同时设置 dashscope.api_key

        return Tongyi(
            model_name=self.config.get("model", "qwen-max"),
            dashscope_api_key=api_key,
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

        # 设置环境变量，确保 dashscope 库能够找到 API key
        api_key = self.config["api_key"]
        if api_key:
            os.environ["DASHSCOPE_API_KEY"] = api_key

        return DashScopeEmbeddings(
            model=self.config.get("model", "text-embedding-v2"),
            dashscope_api_key=api_key,
        )


class MultiModalConversationWrapper:
    """MultiModalConversation 包装器，使其支持 invoke 方法"""

    def __init__(self, conversation: Any, model: str, config: dict):
        """
        初始化包装器
        
        Args:
            conversation: MultiModalConversation 实例（实际上不需要，保留为 None 以保持接口一致性）
            model: 模型名称
            config: 配置字典
        """
        self.conversation = conversation  # 保留为 None，MultiModalConversation 使用静态方法
        self.model = model
        self.config = config

    def invoke(self, messages: list) -> Any:
        """
        调用多模态对话模型（兼容 LangChain 接口）
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": [...]}]
        
        Returns:
            响应对象，包含 content 属性
        """
        from dashscope import MultiModalConversation

        # 调用 MultiModalConversation.call
        response = MultiModalConversation.call(
            model=self.model,
            messages=messages,
            enable_thinking=self.config.get("enable_thinking", False),
            top_p=self.config.get("top_p", 0.5),
        )

        # 创建响应包装器，使其兼容 LangChain 接口
        class ResponseWrapper:
            def __init__(self, response):
                self.response = response
                self._content = None

            @property
            def content(self) -> str:
                """提取回复内容"""
                if self._content is not None:
                    return self._content

                if hasattr(self.response, "status_code") and self.response.status_code == 200:
                    if hasattr(self.response, "output") and hasattr(self.response.output, "choices"):
                        self._content = self.response.output.choices[0].message.content
                        
                    elif isinstance(self.response, dict) and "output" in self.response:
                        if "choices" in self.response["output"]:
                            self._content = self.response["output"]["choices"][0]["message"]["content"]
                
                if self._content is None:
                    raise Exception(
                        f"API 调用失败: {getattr(self.response, 'status_code', 'unknown')}, "
                        f"{getattr(self.response, 'message', str(self.response))}"
                    )
                
                return self._content

        return ResponseWrapper(response)


class DashScopeMultiModalConversationProvider(BaseMultiModalConversationProvider):
    """DashScope MultiModalConversation 提供者"""

    def validate_config(self) -> bool:
        """验证 DashScope MultiModalConversation 配置"""
        if not self.config.get("api_key"):
            raise ValueError("DASHSCOPE_API_KEY 未设置，请在.env文件中配置")
        return True

    def create_instance(self) -> Any:
        """创建 DashScope MultiModalConversation 实例"""
        # 设置环境变量，确保 dashscope 库能够找到 API key
        api_key = self.config["api_key"]
        if api_key:
            os.environ["DASHSCOPE_API_KEY"] = api_key
            # 同时设置 dashscope.api_key，确保兼容性
            import dashscope
            dashscope.api_key = api_key

        model = self.config.get("model", "qwen3-vl-plus-2025-12-19")
        
        # MultiModalConversation 不需要实例化，直接使用静态方法 call()
        # 返回包装器，使其支持 invoke 方法
        return MultiModalConversationWrapper(None, model, self.config)
