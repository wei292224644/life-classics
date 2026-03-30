# 删除 OpenAI + Instructor 结构化输出

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 `instructor` 库依赖及所有非 anthropic provider 的结构化输出实现，统一到仅使用 anthropic streaming tool use。

**Architecture:** 简化 `client_factory.py`，只保留 anthropic 分支；修改 `invoker.py` 兜底为 `"anthropic"`；删除 `pyproject.toml` 中的 instructor 依赖。

**Tech Stack:** Python (uv), instructor (删除), anthropic SDK

---

## 文件变更概览

| 文件 | 变更 |
|------|------|
| `server/pyproject.toml` | 删除 `instructor>=1.14.5` |
| `server/parser/structured_llm/client_factory.py` | 删除 instructor import、`_create_openai_client()`、openai/dashscope/ollama 分支 |
| `server/parser/structured_llm/invoker.py` | 兜底 provider 从 `"openai"` 改为 `"anthropic"` |
| `server/config.py` | 注释去掉 "(Instructor)" |
| `server/README.md` | 更新 instructor 相关文档 |
| `server/pyproject.toml` + `uv.lock` | `uv sync` 更新依赖锁 |

---

## 任务 1：修改 `client_factory.py`

**文件：**
- 修改: `server/parser/structured_llm/client_factory.py`

**变更说明：**
1. 删除 `import instructor`
2. 删除 `_create_openai_client()` 函数
3. `get_structured_client()` 只保留 anthropic 分支，其他 provider 抛 `ValueError`

**变更后预期代码：**

```python
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
            "temperature": temperature,
            "tools": [tool_def],
            "tool_choice": {"type": "tool", "name": tool_name},
            "messages": messages,
            "stream": True,
        }
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        partial_json_chunks: list[str] = []
        text_chunks: list[str] = []
        _debug: list[dict] = []

        with client.messages.create(**create_kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    delta = event.delta
                    delta_type = type(delta).__name__
                    delta_attrs = {k: getattr(delta, k, None) for k in ["partial_json", "text"]}
                    _debug.append({"delta_type": delta_type, "attrs": delta_attrs})
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
            debug=json.dumps(_debug[:5]),
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
```

---

## 任务 2：修改 `invoker.py` 兜底 provider

**文件：**
- 修改: `server/parser/structured_llm/invoker.py:43-53`

**变更：**
```python
# 变更前
return "openai"  # 硬编码兜底

# 变更后
return "anthropic"  # 硬编码兜底
```

---

## 任务 3：更新 `config.py` 注释

**文件：**
- 修改: `server/config.py:56`

**变更：**
```python
# 变更前
# ── Parser Workflow Structured Output（Instructor）────────────────────────

# 变更后
# ── Parser Workflow Structured Output──────────────────────────────
```

---

## 任务 4：更新 `README.md`

**文件：**
- 修改: `server/README.md`

**变更位置 1（概述段落）：**
```python
# 变更前
- **解析**：LangGraph 流水线、`server/parser/rules/` 规则与 Instructor 结构化输出

# 变更后
- **解析**：LangGraph 流水线、`server/parser/rules/` 规则与 Anthropic Streaming Tool Use 结构化输出
```

**变更位置 2（配置表）：**
```python
# 变更前
| `PARSER_STRUCTURED_MAX_RETRIES` | `2` | Instructor 重试 |

# 变更后
| `PARSER_STRUCTURED_MAX_RETRIES` | `2` | 结构化输出重试 |
```

---

## 任务 5：删除 `instructor` 依赖

**文件：**
- 修改: `server/pyproject.toml`

**变更：**
删除 `pyproject.toml` 中的这一行：
```python
instructor>=1.14.5,
```

---

## 任务 6：更新依赖锁

- [ ] **Step 1: 运行 uv sync**

```bash
cd /Users/wwj/Desktop/myself/life-classics/server && uv sync
```

预期：`instructor` 从依赖中移除。

---

## 任务 7：运行测试验证

- [ ] **Step 1: 运行 parser_workflow 相关测试**

```bash
cd /Users/wwj/Desktop/myself/life-classics/server && uv run pytest tests/core/parser_workflow/ -v --tb=short 2>&1 | head -80
```

预期：无失败（`test_structured_llm.py` 已是注释状态，`test_classify_node_fallback.py` 等应通过）。

---

## 任务 8：提交

```bash
git add server/pyproject.toml server/parser/structured_llm/client_factory.py server/parser/structured_llm/invoker.py server/config.py server/README.md
git commit -m "$(cat <<'EOF'
refactor: remove instructor, unify on anthropic streaming tool use

- 删除 instructor>=1.14.5 依赖
- client_factory.py 仅保留 anthropic provider
- resolve_provider_for_node 兜底改为 anthropic
- 更新 config.py 和 README.md 注释

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## 自检清单

- [ ] spec 覆盖：所有 spec 变更点均有对应任务
- [ ] 无 placeholder：所有代码为实际变更后代码，无 TBD/TODO
- [ ] 类型一致性：`get_structured_client(provider, model)` 签名不变，外部调用方无需修改
