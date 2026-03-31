"""按 provider 构建结构化输出客户端（仅 anthropic）。"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

import anthropic
import structlog
from pydantic import BaseModel

from config import settings
from worflow_parser_kb.structured_llm.errors import JsonOutputParseError

_logger = structlog.get_logger(__name__)


def _create_anthropic_client(
    api_key: str,
    base_url: str | None,
) -> Callable[..., BaseModel]:
    """通过 Anthropic SDK + JSON system prompt 创建结构化输出 callable。

    MiniMax-M2.7 是思考型模型，不支持 tool_use 的 InputJSONDelta 流。
    改为在 system 参数注入 JSON Schema 指令，收集 TextDelta 后经三步解析管道提取 JSON。
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
        schema_str = json.dumps(
            response_model.model_json_schema(), ensure_ascii=False, indent=2
        )
        system_message = (
            "你是结构化数据提取助手。严格按以下 JSON Schema 输出，"
            "只返回 JSON 对象，不包含任何解释或 Markdown 代码块。\n\n"
            f"Schema:\n{schema_str}"
        )

        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 102400,
            "temperature": temperature if temperature > 0 else 1.0,  # MiniMax 要求 > 0
            "system": system_message,
            "messages": messages,
            "stream": True,
        }
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        text_chunks: list[str] = []

        with client.messages.create(**create_kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    delta = event.delta
                    # 只收集 TextDelta，跳过 ThinkingDelta / SignatureDelta
                    if hasattr(delta, "text"):
                        text_chunks.append(delta.text)
                elif event.type == "message_stop":
                    break

        text_response = "".join(text_chunks).strip()

        if not text_response:
            raise JsonOutputParseError(
                f"模型返回空响应，model={model!r}，"
                f"response_model={response_model.__name__!r}"
            )

        # 解析管道
        # 1. 直接解析裸 JSON
        try:
            return response_model.model_validate(json.loads(text_response))
        except Exception:
            pass

        # 2. 提取 ```json ... ``` 块
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text_response)
        if match:
            try:
                return response_model.model_validate(json.loads(match.group(1)))
            except Exception:
                pass

        # 3. 提取文本中第一个完整 JSON 对象或数组
        for pattern in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
            match = re.search(pattern, text_response)
            if match:
                try:
                    return response_model.model_validate(json.loads(match.group(0)))
                except Exception:
                    pass

        raise JsonOutputParseError(
            f"JSON 解析失败，model={model!r}，"
            f"response_model={response_model.__name__!r}，"
            f"text_preview={text_response[:200]!r}"
        )

    return _create


def get_structured_client(provider: str, model: str) -> Callable[..., BaseModel]:
    """
    根据 provider 获取可调用的结构化输出客户端。

    仅支持 anthropic。

    返回的 callable 签名：
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
