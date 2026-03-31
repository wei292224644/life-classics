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
from worflow_parser_kb.structured_llm.errors import JsonOutputParseError, StructuredOutputError

_logger = structlog.get_logger(__name__)
_create_structured_fn = create_anthropic_structured()
T = TypeVar("T", bound=BaseModel)

# node_name -> (provider_key, model_key)
_NODE_CONFIG_KEYS = {
    "classify_node": ("CLASSIFY_LLM_PROVIDER", "CLASSIFY_MODEL"),
    "escalate_node": ("ESCALATE_LLM_PROVIDER", "ESCALATE_MODEL"),
    "transform_node": ("TRANSFORM_LLM_PROVIDER", "TRANSFORM_MODEL"),
    "structure_node": ("DOC_TYPE_LLM_PROVIDER", "DOC_TYPE_LLM_MODEL"),
}

_TRANSFORM_FALLBACK_MODEL_KEY = "ESCALATE_MODEL"


def resolve_provider_for_node(node_provider: str | None, global_provider: str | None) -> str:
    if node_provider:
        return node_provider
    if global_provider:
        return global_provider
    return "anthropic"


def resolve_model_for_node(node_name: str, node_model: str, fallback_model: str) -> str:
    if node_name == "transform_node" and not node_model:
        return fallback_model
    return node_model


def _get_provider_and_model_for_node(node_name: str) -> tuple[str, str]:
    keys = _NODE_CONFIG_KEYS.get(node_name)
    if not keys:
        raise ValueError(f"未知 node_name: {node_name!r}")

    provider_key, model_key = keys
    node_provider = getattr(settings, provider_key, "") or ""
    node_model = getattr(settings, model_key, "") or ""
    fallback_model = getattr(settings, _TRANSFORM_FALLBACK_MODEL_KEY, "") or ""

    provider = settings.DEFAULT_LLM_PROVIDER
    model = resolve_model_for_node(node_name, node_model, fallback_model)
    if not model:
        raise ValueError(f"node_name={node_name!r} 解析到的 model 为空")
    return provider, model


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
    resolved_provider = provider
    resolved_model = model
    if resolved_provider is None or resolved_model is None:
        p, m = _get_provider_and_model_for_node(node_name)
        if resolved_provider is None:
            resolved_provider = p
        if resolved_model is None:
            resolved_model = m

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
        # usually consumed by retry in create_fn; keep mapping for direct failures
        raise JsonOutputParseError(str(e)) from e
    except AnthropicStructuredOutputError as e:
        _logger.error(
            "structured_gateway_error",
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

