"""
LLM配置 - 使用统一的模型提供者工厂
支持多种提供者：DashScope/Qwen、Ollama、OpenRouter
"""

from typing import List, Optional, Dict

from langchain_core.messages import BaseMessage
from app.core.providers.factory import ModelFactory


def get_llm(
    provider_name: Optional[str] = None, provider_config: Optional[Dict] = None
):
    """
    获取LLM实例（单例模式）
    使用统一的模型提供者工厂，支持多种提供者

    Args:
        provider_name: 可选的提供者名称，如果为 None 则使用配置中的默认值
                      支持的提供者: "dashscope", "ollama", "openrouter"

    Returns:
        LLM 实例（兼容 LlamaIndex）

    Examples:
        # 使用默认配置的提供者
        llm = get_llm()

        # 使用指定的提供者
        llm = get_llm("ollama")
        llm = get_llm("dashscope")
        llm = get_llm("openrouter")
    Args:
        provider_name: 指定提供者名称（可覆盖配置）
        provider_config: 运行时配置覆盖，例如自定义模型名称、温度等
    """
    return ModelFactory.get_llm(provider_name, provider_config=provider_config)


def get_multimodal(
    provider_name: Optional[str] = None, provider_config: Optional[Dict] = None
):
    """
    获取多模态对话实例（单例模式）
    使用统一的模型提供者工厂，支持多模态对话（如图片理解）

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
    return ModelFactory.get_multimodal(provider_name, provider_config=provider_config)


def chat(
    messages: List[BaseMessage],
    provider_name: Optional[str] = None,
    provider_config: Optional[Dict] = None,
) -> str:
    """
    与LLM进行对话
    """
    llm = get_llm(provider_name, provider_config=provider_config)
    response = llm.invoke(messages)
    if hasattr(response, "content"):
        return response.content
    elif isinstance(response, str):
        return response
    else:
        return str(response)


async def chat_stream(
    messages: List[BaseMessage],
    provider_name: Optional[str] = None,
    provider_config: Optional[Dict] = None,
):
    """
    与LLM进行流式对话
    
    Yields:
        str: 流式返回的文本块
    """
    llm = get_llm(provider_name, provider_config=provider_config)
    
    # 尝试使用流式方法
    if hasattr(llm, "astream"):
        async for chunk in llm.astream(messages):
            if hasattr(chunk, "content"):
                yield chunk.content
            elif isinstance(chunk, str):
                yield chunk
            else:
                yield str(chunk)
    elif hasattr(llm, "stream"):
        for chunk in llm.stream(messages):
            if hasattr(chunk, "content"):
                yield chunk.content
            elif isinstance(chunk, str):
                yield chunk
            else:
                yield str(chunk)
    else:
        # 如果不支持流式，回退到普通调用
        response = llm.invoke(messages)
        if hasattr(response, "content"):
            yield response.content
        elif isinstance(response, str):
            yield response
        else:
            yield str(response)
