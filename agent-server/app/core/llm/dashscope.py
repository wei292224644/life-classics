"""
DashScope/Qwen 提供者实现
"""

import os
from typing import Any

import dashscope
from langchain_community.llms import Tongyi
from langchain_community.embeddings import DashScopeEmbeddings

from app.core.config import settings
from app.core.llm.utils import get_cache, get_cache_key, set_cache


api_key = settings.DASHSCOPE_API_KEY

# 设置环境变量和 dashscope.api_key
if api_key:
    os.environ["DASHSCOPE_API_KEY"] = api_key
    dashscope.api_key = api_key


def create_chat(model: str, **kwargs) -> Tongyi:
    cache_key = get_cache_key(f"dashscope_{model}", kwargs)
    cached_instance = get_cache(cache_key)
    if cached_instance is not None:
        return cached_instance

    instance = Tongyi(
        model_name=model,
        dashscope_api_key=api_key,
        temperature=kwargs.get("temperature", 0.7),
        max_tokens=kwargs.get("max_tokens", 2048),
    )
    set_cache(cache_key, instance)
    return instance


def create_embedding(model: str, **kwargs) -> DashScopeEmbeddings:
    cache_key = get_cache_key(f"dashscope_embedding_{model}", kwargs)
    cached_instance = get_cache(cache_key)
    if cached_instance is not None:
        return cached_instance

    instance = DashScopeEmbeddings(
        model=model,
        dashscope_api_key=api_key,
    )
    set_cache(cache_key, instance)
    return instance


class MultiModalConversationWrapper:
    """MultiModalConversation 包装器，使其支持 invoke 方法"""

    def __init__(self, model: str, **kwargs):
        """
        初始化包装器

        Args:
            model: 模型名称
            **kwargs: 配置参数
        """
        self.model = model
        self.config = kwargs

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


def create_multimodal(model: str, **kwargs) -> MultiModalConversationWrapper:
    cache_key = get_cache_key(f"dashscope_multimodal_{model}", kwargs)
    cached_instance = get_cache(cache_key)
    if cached_instance is not None:
        return cached_instance

    instance = MultiModalConversationWrapper(model=model, **kwargs)
    set_cache(cache_key, instance)
    return instance
