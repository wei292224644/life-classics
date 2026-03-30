"""按 provider 构建结构化输出客户端（仅 anthropic）。"""

from __future__ import annotations

import json
from typing import Any, Callable

import anthropic
import structlog
from pydantic import BaseModel

from config import settings

_logger = structlog.get_logger(__name__)


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
            "temperature": temperature if temperature > 0 else 1.0,  # MiniMax 要求 > 0
            "tools": [tool_def],
            "tool_choice": {"type": "tool", "name": tool_name},
            "messages": messages,
            "stream": True,
        }
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        partial_json_chunks: list[str] = []
        text_chunks: list[str] = []
        all_events: list[dict] = []

        with client.messages.create(**create_kwargs) as stream:
            for event in stream:
                # 记录所有事件类型用于 debug
                event_dict = {"type": event.type}
                if hasattr(event, "delta"):
                    delta = event.delta
                    event_dict["delta_type"] = type(delta).__name__
                    if hasattr(delta, "partial_json"):
                        event_dict["partial_json"] = delta.partial_json
                    if hasattr(delta, "text"):
                        event_dict["text"] = delta.text
                all_events.append(event_dict)

                if event.type == "content_block_delta":
                    delta = event.delta
                    # InputJSONDelta.partial_json 是增量 JSON 字符串
                    if hasattr(delta, "partial_json") and delta.partial_json:
                        partial_json_chunks.append(delta.partial_json)
                    # TextDelta 是普通文本（模型未走 tool_use 时的 fallback）
                    elif hasattr(delta, "text"):
                        text_chunks.append(delta.text)
                elif event.type == "message_stop":
                    break

        # 优先用 tool_use JSON 解析
        if partial_json_chunks:
            tool_input = json.loads("".join(partial_json_chunks))
            return response_model(**tool_input)

        _logger.warning(
            "anthropic_tool_use_no_json_delta",
            model=model,
            tool_name=tool_name,
            partial_count=len(partial_json_chunks),
            text_count=len(text_chunks),
            text_preview="".join(text_chunks)[:500] if text_chunks else "",
            all_event_types=[e.get("type") for e in all_events],
            all_deltas=[{k: v for k, v in e.items() if k != "type"} for e in all_events if e.get("type") == "content_block_delta"],
        )

        # Fallback：模型返回了普通文本，直接解析其中的 JSON
        if text_chunks:
            _logger.warning(
                "anthropic_tool_use_fallback_to_text",
                model=model,
                tool_name=tool_name,
            )
            text_response = "".join(text_chunks)
            # 尝试直接解析（模型可能直接返回了 JSON）
            try:
                return response_model(**json.loads(text_response))
            except Exception:
                pass
            # 尝试提取 ```json ... ``` 包裹的 JSON
            import re
            match = re.search(r"```json\s*([\s\S]*?)\s*```", text_response)
            if match:
                try:
                    return response_model(**json.loads(match.group(1)))
                except Exception:
                    pass
            raise ValueError(
                f"Anthropic fallback 解析失败，model={model!r}，"
                f"response_model={tool_name!r}，text_preview={text_response[:200]!r}"
            )

        raise ValueError(
            f"Anthropic 响应中未找到 tool_use block，model={model!r}，"
            f"response_model={tool_name!r}"
        )

    return _create


def get_structured_client(provider: str, model: str) -> Callable[..., BaseModel]:
    """
    根据 provider 获取可调用的结构化输出客户端（返回 chat.completions.create 的 callable）。

    仅支持 anthropic。

    返回的 callable 签名兼容：
        create(model=..., messages=..., response_model=..., temperature=..., ...) -> BaseModel
    """
    if provider == "anthropic":
        return _create_anthropic_client(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL or None,
        )
    else:
        raise ValueError(
            f"未知 provider: {provider!r}。仅支持 anthropic"
        )
