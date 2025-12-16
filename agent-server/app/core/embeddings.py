"""
嵌入模型配置 - 使用统一的模型提供者工厂
支持多种提供者：DashScope/Qwen、Ollama、OpenRouter
可以独立于 LLM 提供者进行配置
"""

from typing import Optional, Dict
from app.core.providers.factory import ModelFactory


def get_embedding_model(
    provider_name: Optional[str] = None, provider_config: Optional[Dict] = None
):
    """
    获取嵌入模型实例（单例模式）
    使用统一的模型提供者工厂，支持多种提供者
    可以独立于 LLM 提供者进行配置

    Args:
        provider_name: 可选的提供者名称，如果为 None 则使用配置中的默认值
                      支持的提供者: "dashscope", "ollama", "openrouter"

    Returns:
        Embedding 实例（兼容 LlamaIndex）

    Examples:
        # 使用默认配置的提供者
        embedding = get_embedding_model()

        # 使用指定的提供者
        embedding = get_embedding_model("ollama")
        embedding = get_embedding_model("dashscope")
        embedding = get_embedding_model("openrouter")

    Note:
        Embedding 提供者可以独立于 LLM 提供者配置。
        例如：LLM 使用 ollama，Embedding 使用 dashscope
    Args:
        provider_name: 指定提供者名称（可覆盖配置）
        provider_config: 运行时配置覆盖，例如自定义模型名称、base_url 等
    """
    return ModelFactory.get_embedding(provider_name, provider_config=provider_config)
