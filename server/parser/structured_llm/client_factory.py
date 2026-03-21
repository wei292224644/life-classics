"""按 provider 构建 Instructor 可调用客户端。"""

from __future__ import annotations

from typing import Any, Callable

import instructor
from pydantic import BaseModel

from config import settings


def _create_openai_client(
    model_ref: str,
    api_key: str,
    base_url: str | None,
    **extra_kwargs: Any,
) -> instructor.Instructor:
    """通过 from_provider 创建 Instructor 客户端。"""
    return instructor.from_provider(
        model_ref,
        mode=instructor.Mode.MD_JSON,
        api_key=api_key,
        base_url=base_url,
        timeout=settings.PARSER_STRUCTURED_TIMEOUT_SECONDS,
        **extra_kwargs,
    )


def get_structured_client(provider: str, model: str) -> Callable[..., BaseModel]:
    """
    根据 provider 获取可调用的 Instructor 客户端（返回 chat.completions.create 的 callable）。

    支持的 provider：
    - openai: 使用 LLM_API_KEY / LLM_BASE_URL
    - dashscope: 使用 DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL
    - ollama: 使用 OLLAMA_BASE_URL

    返回的 callable 签名兼容：
        create(model=..., messages=..., response_model=..., temperature=..., ...) -> BaseModel
    """
    if provider == "openai":
        client = _create_openai_client(
            model_ref=f"openai/{model}",
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL or None,
        )
    elif provider == "dashscope":
        client = _create_openai_client(
            # DashScope 走 OpenAI-compatible 接口
            model_ref=f"openai/{model}",
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
        )
        # dashscope 需在每次请求注入 enable_thinking=False，由 _create 传入 extra_body
    elif provider == "ollama":
        # Ollama 通常无需 api_key，base_url 指向本地
        client = _create_openai_client(
            model_ref=f"ollama/{model}",
            api_key="ollama",  # ollama 本地无需真实 key，传占位即可
            base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
        )
    else:
        raise ValueError(
            f"未知 provider: {provider!r}。支持的 provider：openai, dashscope, ollama"
        )

    def _create(
        model: str,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
        temperature: float = 0.0,
        timeout: int | None = None,
        extra_body: dict | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "response_model": response_model,
            "temperature": temperature,
            "timeout": timeout or settings.PARSER_STRUCTURED_TIMEOUT_SECONDS,
            # "max_tokens": 8192,
            "extra_body": extra_body,
            **kwargs,
        }
        return client.chat.completions.create(**create_kwargs)

    return _create
