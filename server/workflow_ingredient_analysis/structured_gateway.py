"""LLM structured output gateway for ingredient_analysis workflow."""
from __future__ import annotations

from typing import Any, TypeVar

import structlog
from pydantic import BaseModel

from config import settings
from llm.anthropic import (
    JsonOutputParseError as AnthropicJsonOutputParseError,
)
from llm.anthropic import (
    StructuredOutputError as AnthropicStructuredOutputError,
)
from llm.anthropic import create_structured as create_anthropic_structured
from observability.metrics import llm_tokens_total
from workflow_parser_kb.structured_llm.errors import JsonOutputParseError, StructuredOutputError

_logger = structlog.get_logger(__name__)
_create_structured_fn = create_anthropic_structured()
T = TypeVar("T", bound=BaseModel)


def invoke_structured(
    *,
    node_name: str,
    prompt: str,
    response_model: type[T],
    provider: str | None = None,
    model: str | None = None,
    max_retries: int | None = None,
    temperature: float | None = None,
    timeout_seconds: int | None = None,
    extra_body: dict | None = None,
    **kwargs: Any,
) -> T:
    resolved_provider = provider or settings.DEFAULT_LLM_PROVIDER
    resolved_model = model or settings.DEFAULT_MODEL

    if resolved_provider != "anthropic":
        raise ValueError(f"structured output 仅支持 anthropic，当前 provider={resolved_provider!r}")

    max_retries = max_retries if max_retries is not None else settings.PARSER_STRUCTURED_MAX_RETRIES
    temperature = temperature if temperature is not None else settings.PARSER_STRUCTURED_TEMPERATURE
    timeout_seconds = (
        timeout_seconds if timeout_seconds is not None else settings.PARSER_STRUCTURED_TIMEOUT_SECONDS
    )

    try:
        result = _create_structured_fn(
            model=resolved_model,
            messages=[{"role": "user", "content": prompt}],
            response_model=response_model,
            max_retries=max_retries,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            extra_body=extra_body or {},
            **kwargs,
        )
        usage = getattr(result, "usage", None)
        if usage:
            llm_tokens_total.labels(node=node_name, model=resolved_model, type="prompt").inc(
                usage.prompt_tokens or 0
            )
            llm_tokens_total.labels(node=node_name, model=resolved_model, type="completion").inc(
                usage.completion_tokens or 0
            )
        return result
    except AnthropicJsonOutputParseError as e:
        raise JsonOutputParseError(str(e)) from e
    except AnthropicStructuredOutputError as e:
        _logger.error(
            "ingredient_analysis_gateway_error",
            node_name=node_name,
            provider=e.provider,
            model=e.model,
            response_model=e.response_model,
            retry_count=e.retry_count,
            error=e.raw_error,
        )
        raise StructuredOutputError(
            str(e),
            provider=e.provider,
            model=e.model,
            node_name=node_name,
            response_model=e.response_model,
            retry_count=e.retry_count,
            raw_error=e.raw_error,
        ) from e
