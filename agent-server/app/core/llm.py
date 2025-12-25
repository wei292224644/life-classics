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
