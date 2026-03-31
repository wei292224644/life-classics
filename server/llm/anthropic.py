"""
Anthropic provider implementation.

- create_chat: plain chat callable factory
- create_structured: structured output callable factory
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, TypeVar

import anthropic
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from config import settings

T = TypeVar("T", bound=BaseModel)


class JsonOutputParseError(RuntimeError):
    """Raised when model output cannot be parsed as JSON."""


class StructuredOutputError(RuntimeError):
    """Raised when structured output call failed after retries."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str,
        response_model: str,
        retry_count: int,
        raw_error: str,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.response_model = response_model
        self.retry_count = retry_count
        self.raw_error = raw_error


def create_chat(
    api_key: str | None = None,
    base_url: str | None = None,
) -> Callable[..., Any]:
    """
    Build a plain anthropic chat callable.

    The returned callable forwards runtime controls from caller.
    """
    client = anthropic.Anthropic(
        api_key=api_key or settings.ANTHROPIC_API_KEY,
        base_url=base_url if base_url is not None else (settings.ANTHROPIC_BASE_URL or None),
    )

    def _create_chat(
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        timeout_seconds: int | None = None,
        max_tokens: int = 4096,
        extra_body: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature > 0 else 1.0,
            "max_tokens": max_tokens,
        }
        if timeout_seconds is not None:
            create_kwargs["timeout"] = timeout_seconds
        if extra_body:
            create_kwargs["extra_body"] = extra_body
        create_kwargs.update(kwargs)
        return client.messages.create(**create_kwargs)

    return _create_chat


def create_structured(
    api_key: str | None = None,
    base_url: str | None = None,
) -> Callable[..., T]:
    """
    Build a structured-output callable with retry and JSON parsing pipeline.

    Note:
    - Only anthropic credentials are read here.
    - Runtime controls (retry/timeout/temperature/extra_body) are passed by caller.
    """
    client = anthropic.Anthropic(
        api_key=api_key or settings.ANTHROPIC_API_KEY,
        base_url=base_url if base_url is not None else (settings.ANTHROPIC_BASE_URL or None),
    )

    def _parse_to_model(text_response: str, response_model: type[T]) -> T:
        # 1) Parse raw JSON
        try:
            return response_model.model_validate(json.loads(text_response))
        except Exception:
            pass

        # 2) Parse fenced json block
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text_response)
        if match:
            try:
                return response_model.model_validate(json.loads(match.group(1)))
            except Exception:
                pass

        # 3) Parse first json object/array in text
        for pattern in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
            match = re.search(pattern, text_response)
            if match:
                try:
                    return response_model.model_validate(json.loads(match.group(0)))
                except Exception:
                    pass

        raise JsonOutputParseError(
            f"JSON 解析失败，response_model={response_model.__name__!r}，text_preview={text_response[:200]!r}"
        )

    def _is_retryable_error(err: Exception) -> bool:
        if isinstance(
            err,
            (
                JsonOutputParseError,
                TimeoutError,
                ConnectionError,
                anthropic.APITimeoutError,
                anthropic.APIConnectionError,
                anthropic.RateLimitError,
                anthropic.InternalServerError,
            ),
        ):
            return True
        if isinstance(err, (anthropic.AuthenticationError, anthropic.BadRequestError)):
            return False
        if getattr(err, "status_code", 0) >= 500:
            return True
        err_type = type(err).__name__
        return (
            err_type in {
                "ReadTimeout",
                "ConnectTimeout",
                "ConnectError",
                "PoolTimeout",
                "WriteTimeout",
                "APITimeoutError",
                "RequestTimeoutError",
                "Timeout",
            }
            or "timeout" in err_type.lower()
            or "timed out" in str(err).lower()
        )

    def _create(
        *,
        model: str,
        messages: list[dict[str, str]],
        response_model: type[T],
        max_retries: int,
        temperature: float,
        timeout_seconds: int | None,
        extra_body: dict[str, Any] | None = None,
        max_tokens: int = 102400,
        **kwargs: Any,
    ) -> T:
        schema_str = json.dumps(response_model.model_json_schema(), ensure_ascii=False, indent=2)
        system_message = (
            "你是结构化数据提取助手。严格按以下 JSON Schema 输出，"
            "只返回 JSON 对象，不包含任何解释或 Markdown 代码块。\n\n"
            f"Schema:\n{schema_str}"
        )

        last_error: Exception | None = None
        retry_count = 0

        for attempt in range(max_retries + 1):
            try:
                create_kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature if temperature > 0 else 1.0,
                    "system": system_message,
                    "messages": messages,
                    "stream": True,
                }
                if timeout_seconds is not None:
                    create_kwargs["timeout"] = timeout_seconds
                if extra_body:
                    create_kwargs["extra_body"] = extra_body
                create_kwargs.update(kwargs)

                text_chunks: list[str] = []
                with client.messages.create(**create_kwargs) as stream:
                    for event in stream:
                        if event.type == "content_block_delta":
                            delta = event.delta
                            if hasattr(delta, "text"):
                                text_chunks.append(delta.text)
                        elif event.type == "message_stop":
                            break

                text_response = "".join(text_chunks).strip()
                if not text_response:
                    raise JsonOutputParseError(
                        f"模型返回空响应，model={model!r}，response_model={response_model.__name__!r}"
                    )
                return _parse_to_model(text_response, response_model)
            except PydanticValidationError as e:
                raise StructuredOutputError(
                    "结构化输出校验失败",
                    provider="anthropic",
                    model=model,
                    response_model=response_model.__name__,
                    retry_count=attempt,
                    raw_error=str(e),
                ) from e
            except Exception as e:
                if not _is_retryable_error(e):
                    raise e
                last_error = e
                retry_count = attempt + 1
                if attempt >= max_retries:
                    break
                continue

        raw_err = str(last_error)[:500] if last_error else "unknown"
        raise StructuredOutputError(
            f"结构化输出调用失败（重试 {retry_count} 次）",
            provider="anthropic",
            model=model,
            response_model=response_model.__name__,
            retry_count=retry_count,
            raw_error=raw_err,
        ) from last_error

    return _create

