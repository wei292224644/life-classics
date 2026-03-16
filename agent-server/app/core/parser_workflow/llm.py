from __future__ import annotations

from typing import Type

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings


def resolve_provider(node_provider: str | None) -> str:
    """
    Provider 解析优先级：
    1. node_provider（节点级 settings 字段）
    2. settings.PARSER_LLM_PROVIDER（全局默认）
    3. "openai"（硬编码兜底）
    """
    if node_provider:
        return node_provider
    if settings.PARSER_LLM_PROVIDER:
        return settings.PARSER_LLM_PROVIDER
    return "openai"


def create_chat_model(
    model: str,
    provider: str,
    output_schema: Type[BaseModel] | dict | None = None,
    **kwargs,
) -> Runnable:
    """
    根据 provider 创建对应的 LangChain chat model。

    支持的 provider：
    - "openai"    → ChatOpenAI，使用 LLM_API_KEY / LLM_BASE_URL
    - "dashscope" → ChatOpenAI，使用 DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL，
                    自动注入 extra_body={"enable_thinking": False}
    - "ollama"    → ChatOllama，使用 OLLAMA_BASE_URL

    若传入 output_schema，返回 llm.with_structured_output(output_schema)。
    未知 provider 抛出 ValueError。
    """
    if provider == "openai":
        llm = ChatOpenAI(
            model=model,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL or None,
            **kwargs,
        )
    elif provider == "dashscope":
        # 自动注入 enable_thinking=False，禁用通义千问思考模式，避免影响 structured output
        extra_body = {**kwargs.pop("extra_body", {}), "enable_thinking": False}
        llm = ChatOpenAI(
            model=model,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            extra_body=extra_body,
            **kwargs,
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama  # type: ignore[import]

        llm = ChatOllama(
            model=model,
            base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
            **kwargs,
        )
    else:
        raise ValueError(
            f"未知 provider: {provider!r}。支持的 provider：openai, dashscope, ollama"
        )

    if output_schema is not None:
        return llm.with_structured_output(output_schema)
    return llm
