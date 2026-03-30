"""按 provider 构建 Instructor 可调用客户端。"""

from __future__ import annotations

import json
from typing import Any, Callable

import anthropic
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
        mode=instructor.Mode.JSON,
        api_key=api_key,
        base_url=base_url,
        timeout=settings.PARSER_STRUCTURED_TIMEOUT_SECONDS,
        **extra_kwargs,
    )


def _create_anthropic_client(
    api_key: str,
    base_url: str | None,
) -> Callable[..., BaseModel]:
    """通过 Anthropic SDK + streaming tool use 创建结构化输出 callable。

    MiniMax 2.7 等模型单次请求可能超过 10 分钟，必须使用流式接口。
    实现：stream=True → 遍历事件流，收集 content_block_delta 中的 InputJSONDelta，
    拼合 partial_json 后解析为 response_model 实例。
    """
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
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
        tool_name = response_model.__name__
        tool_def = {
            "name": tool_name,
            "description": f"返回结构化数据：{tool_name}",
            "input_schema": response_model.model_json_schema(),
        }
        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 102400,
            "temperature": temperature,
            "tools": [tool_def],
            "tool_choice": {"type": "tool", "name": tool_name},
            "messages": messages,
            "stream": True,
        }
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        partial_json_chunks: list[str] = []

        with client.messages.create(**create_kwargs) as stream:
            for event in stream:
                # content_block_delta 事件包含 InputJSONDelta 或 TextDelta
                if event.type == "content_block_delta":
                    delta = event.delta
                    # InputJSONDelta.partial_json 是增量 JSON 字符串
                    if hasattr(delta, "partial_json") and delta.partial_json:
                        partial_json_chunks.append(delta.partial_json)
                elif event.type == "message_stop":
                    break

        if not partial_json_chunks:
            raise ValueError(
                f"Anthropic 响应中未找到 tool_use block，model={model!r}，"
                f"response_model={tool_name!r}"
            )

        tool_input = json.loads("".join(partial_json_chunks))
        return response_model(**tool_input)

    return _create


def get_structured_client(provider: str, model: str) -> Callable[..., BaseModel]:
    """
    根据 provider 获取可调用的 Instructor 客户端（返回 chat.completions.create 的 callable）。

    支持的 provider：
    - openai: 使用 LLM_API_KEY / LLM_BASE_URL
    - dashscope: 使用 DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL
    - ollama: 使用 OLLAMA_BASE_URL
    - anthropic: 使用 ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL（Streaming tool use）

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
    elif provider == "anthropic":
        return _create_anthropic_client(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL or None,
        )
    else:
        raise ValueError(
            f"未知 provider: {provider!r}。支持的 provider：openai, dashscope, ollama, anthropic"
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
