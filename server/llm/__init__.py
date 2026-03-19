"""
LLM 统一接口
提供 Chat、Embedding、多模态等功能
"""

from typing import List, Optional, Dict, Any, AsyncIterator
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from config import settings
from llm.dashscope import (
    create_chat as create_chat_dashscope,
    create_embedding as create_embedding_dashscope,
)
from llm.ollama import (
    create_chat as create_chat_ollama,
    create_embedding as create_embedding_ollama,
)


def get_llm(provider_name: str, model: str, **kwargs) -> BaseChatModel:
    """
    获取LLM实例（带缓存）

    Args:
        provider_name: 可选的提供者名称，如果为 None 则使用配置中的默认值
                      支持的提供者: "dashscope", "ollama", "openrouter"
        provider_config: 运行时配置覆盖，例如自定义模型名称、温度等

    Returns:
        LLM 实例（兼容 LlamaIndex）

    Examples:
        # 使用默认配置的提供者
        llm = get_llm()

        # 使用指定的提供者
        llm = get_llm("ollama")
        llm = get_llm("dashscope", model="qwen-max", temperature=0.8)
    """

    if provider_name == "dashscope":
        return create_chat_dashscope(model=model, **kwargs)
    elif provider_name == "ollama":
        return create_chat_ollama(model=model, **kwargs)
    else:
        raise ValueError(f"不支持的 LLM 提供者: {provider_name}")


def get_multimodal(provider_name: str, model: str, **kwargs) -> Any:
    """
    获取多模态对话实例（带缓存）

    Args:
        provider_name: 可选的提供者名称，如果为 None 则使用 "dashscope"
                      支持的提供者: "dashscope"
        provider_config: 运行时配置覆盖，例如自定义模型名称、温度等

    Returns:
        多模态对话实例（支持 invoke 方法）

    Examples:
        # 使用默认配置的多模态提供者
        multimodal = get_multimodal()

        # 使用指定的提供者和配置
        multimodal = get_multimodal("dashscope", {"model": "qwen3-vl-plus-2025-12-19"})
    """

    # 创建新实例（create_multimodal 内部已处理缓存）
    if provider_name == "dashscope":
        from llm.dashscope import create_multimodal

        return create_multimodal(model=model, **kwargs)
    else:
        raise ValueError(f"不支持的多模态提供者: {provider_name}")


def get_embedding(provider_name: str, model: str, **kwargs) -> Embeddings:
    """
    获取嵌入模型实例（带缓存）
    使用统一的模型提供者工厂，支持多种提供者
    可以独立于 LLM 提供者进行配置

    Args:
        provider_name: 可选的提供者名称，如果为 None 则使用配置中的默认值
                      支持的提供者: "dashscope", "ollama", "openrouter"
        provider_config: 运行时配置覆盖，例如自定义模型名称、base_url 等

    Returns:
        Embedding 实例（兼容 LlamaIndex）

    Examples:
        # 使用默认配置的提供者
        embedding = get_embedding()

        # 使用指定的提供者
        embedding = get_embedding("ollama")
        embedding = get_embedding("dashscope")
        embedding = get_embedding("openrouter")

    Note:
        Embedding 提供者可以独立于 LLM 提供者配置。
        例如：LLM 使用 ollama，Embedding 使用 dashscope
    """
    if provider_name == "dashscope":
        return create_embedding_dashscope(model=model, **kwargs)
    elif provider_name == "ollama":
        return create_embedding_ollama(model=model, **kwargs)
    else:
        raise ValueError(f"不支持的 Embedding 提供者: {provider_name}")


def chat(
    messages: List[BaseMessage],
    provider_name: str,
    model: str,
    provider_config: Dict = {},
) -> str | list[str | dict]:
    """
    与LLM进行对话
    """
    llm = get_llm(provider_name, model, **provider_config)
    response = llm.invoke(messages)
    # 处理不同的返回类型：
    # - ChatModel (如 ChatOllama) 返回 AIMessage，有 content 属性
    # - LLM (如 Tongyi) 直接返回字符串
    if isinstance(response, str):
        return response
    elif hasattr(response, "content"):
        return response.content
    else:
        # 如果既不是字符串也没有 content 属性，尝试转换为字符串
        return str(response)


async def chat_stream(
    messages: List[BaseMessage],
    provider_name: str,
    model: str,
    provider_config: Dict = {},
) -> AsyncIterator[str | list[str | dict]]:
    """
    与LLM进行流式对话

    Yields:
        str: 流式返回的文本块
    """
    llm = get_llm(provider_name, model, **provider_config)

    # 尝试使用流式方法
    if hasattr(llm, "astream"):
        async for chunk in llm.astream(messages):
            # 处理不同的返回类型
            if isinstance(chunk, str):
                yield chunk
            elif hasattr(chunk, "content"):
                yield chunk.content
            else:
                yield str(chunk)
    elif hasattr(llm, "stream"):
        for chunk in llm.stream(messages):
            # 处理不同的返回类型
            if isinstance(chunk, str):
                yield chunk
            elif hasattr(chunk, "content"):
                yield chunk.content
            else:
                yield str(chunk)
    else:
        # 如果不支持流式，回退到普通调用
        response = llm.invoke(messages)
        # 处理不同的返回类型
        if isinstance(response, str):
            yield response
        elif hasattr(response, "content"):
            yield response.content
        else:
            yield str(response)


# 导出统一接口
__all__ = [
    "get_llm",
    "get_embedding",
    "get_multimodal",
    "chat",
    "chat_stream",
]
