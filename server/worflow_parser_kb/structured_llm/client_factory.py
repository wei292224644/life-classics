"""按 provider 构建结构化输出客户端（仅 anthropic）。"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from config import settings
from llm.anthropic import create_structured as _create_anthropic_structured

T = TypeVar("T", bound=BaseModel)


def get_structured_client(provider: str, model: str) -> Callable[..., T]:
    """
    根据 provider 获取可调用的结构化输出客户端。

    仅支持 anthropic。
    内部使用 server/llm/anthropic.create_structured()。

    返回的 callable 签名：
        create(model=..., messages=..., response_model=..., temperature=..., ...) -> BaseModel
    """
    if provider != "anthropic":
        raise ValueError(
            f"未知 provider: {provider!r}。仅支持 anthropic"
        )

    # 使用 server/llm/anthropic.create_structured()，内部已包含重试和 JSON 解析逻辑
    create_fn = _create_anthropic_structured()

    def _create(
        model: str,
        messages: list[dict[str, str]],
        response_model: type[T],
        temperature: float = 0.0,
        timeout: int | None = None,
        extra_body: dict | None = None,
        **kwargs: Any,
    ) -> T:
        # 将 timeout 映射为 timeout_seconds（create_structured 的参数名）
        return create_fn(
            model=model,
            messages=messages,
            response_model=response_model,
            max_retries=settings.PARSER_STRUCTURED_MAX_RETRIES,
            temperature=temperature,
            timeout_seconds=timeout,
            extra_body=extra_body or {},
            **kwargs,
        )

    return _create
