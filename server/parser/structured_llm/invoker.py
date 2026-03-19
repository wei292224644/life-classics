"""统一执行结构化请求（response_model、重试、超时、参数注入）。"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from config import settings
from parser.structured_llm.client_factory import get_structured_client
from parser.structured_llm.errors import StructuredOutputError

T = TypeVar("T", bound=BaseModel)

# node_name -> (provider_key, model_key)
_NODE_CONFIG_KEYS = {
    "classify_node": ("CLASSIFY_LLM_PROVIDER", "CLASSIFY_MODEL"),
    "escalate_node": ("ESCALATE_LLM_PROVIDER", "ESCALATE_MODEL"),
    "transform_node": ("TRANSFORM_LLM_PROVIDER", "TRANSFORM_MODEL"),
    "structure_node": ("DOC_TYPE_LLM_PROVIDER", "DOC_TYPE_LLM_MODEL"),
}

# transform_node 的 model fallback 来源
_TRANSFORM_FALLBACK_MODEL_KEY = "ESCALATE_MODEL"


def resolve_provider_for_node(
    node_provider: str | None,
    global_provider: str | None,
) -> str:
    """
    Provider 解析优先级：
    1. node_provider（节点级覆盖）
    2. global_provider（PARSER_LLM_PROVIDER）
    3. "openai"（硬编码兜底）
    """
    if node_provider:
        return node_provider
    if global_provider:
        return global_provider
    return "openai"


def resolve_model_for_node(
    node_name: str,
    node_model: str,
    fallback_model: str,
) -> str:
    """
    解析节点使用的模型。

    - transform_node 且 node_model 为空时，返回 fallback_model
    - 其他情况返回 node_model（即使为空）
    """
    if node_name == "transform_node" and not node_model:
        return fallback_model
    return node_model


def _get_provider_and_model_for_node(node_name: str) -> tuple[str, str]:
    """按 node_name 从 settings 解析 provider 和 model。"""
    keys = _NODE_CONFIG_KEYS.get(node_name)
    if not keys:
        raise ValueError(f"未知 node_name: {node_name!r}")

    provider_key, model_key = keys
    node_provider = getattr(settings, provider_key, "") or ""
    node_model = getattr(settings, model_key, "") or ""
    fallback_model = getattr(settings, _TRANSFORM_FALLBACK_MODEL_KEY, "") or ""

    provider = resolve_provider_for_node(
        node_provider or None,
        settings.PARSER_LLM_PROVIDER or None,
    )

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
    """
    统一执行结构化输出调用。

    - 若 provider/model 未显式传入，则按 node_name 从 settings 解析
    - 对可恢复错误（TimeoutError、ConnectionError 等）重试
    - 对不可恢复错误（Pydantic ValidationError）不重试，直接抛 StructuredOutputError
    """
    resolved_provider = provider
    resolved_model = model
    if resolved_provider is None or resolved_model is None:
        p, m = _get_provider_and_model_for_node(node_name)
        if resolved_provider is None:
            resolved_provider = p
        if resolved_model is None:
            resolved_model = m

    max_retries = (
        max_retries
        if max_retries is not None
        else settings.PARSER_STRUCTURED_MAX_RETRIES
    )
    temperature = (
        temperature
        if temperature is not None
        else settings.PARSER_STRUCTURED_TEMPERATURE
    )
    timeout_seconds = (
        timeout_seconds
        if timeout_seconds is not None
        else settings.PARSER_STRUCTURED_TIMEOUT_SECONDS
    )

    create_fn = get_structured_client(resolved_provider, resolved_model)
    messages = [{"role": "user", "content": prompt}]

    last_error: Exception | None = None
    retry_count = 0

    # for attempt in range(max_retries + 1):
    try:

        result = create_fn(
            model=resolved_model,
            messages=messages,
            response_model=response_model,
            temperature=temperature,
            timeout=timeout_seconds,
            extra_body=extra_body or {},
            **kwargs,
        )
        return result
    except PydanticValidationError as e:
        raise StructuredOutputError(
            f"结构化输出校验失败: {node_name} {messages}",
            provider=resolved_provider,
            model=resolved_model,
            node_name=node_name,
            response_model=response_model.__name__,
            # retry_count=attempt,
            raw_error=str(e),
        ) from e
    # except (TimeoutError, ConnectionError) as e:
    #     last_error = e
    #     retry_count = attempt + 1
    #     if attempt >= max_retries:
    #         break
    #     continue
    except Exception as e:
        print(e)
        print("=" * 100)
        print(messages)
        raise e

    # raw_err = str(last_error)[:500] if last_error else "unknown"
    # raise StructuredOutputError(
    #     f"结构化输出调用失败（重试 {retry_count} 次）: {node_name}",
    #     provider=resolved_provider,
    #     model=resolved_model,
    #     node_name=node_name,
    #     response_model=response_model.__name__,
    #     retry_count=retry_count,
    #     raw_error=raw_err,
    # ) from last_error
