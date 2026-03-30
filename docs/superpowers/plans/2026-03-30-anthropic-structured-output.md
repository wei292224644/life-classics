# Anthropic SDK + Tool Use 替换 Instructor 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `structured_llm/` 模块内新增 `anthropic` provider，使用 Anthropic SDK + tool use 实现结构化输出，替代 instructor JSON mode，对上层 nodes 完全透明。

**Architecture:** 新增 `_create_anthropic_client()` 函数，返回与现有 `_create()` 签名完全兼容的 callable；`invoker.py` 扩展 `_is_retryable` 识别 anthropic 异常；config 层增加独立的 `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` 字段。

**Tech Stack:** Python 3.12, anthropic SDK, Pydantic v2, pytest, uv

---

## 文件变更清单

| 文件 | 操作 |
|---|---|
| `server/config.py` | 修改：新增 2 个字段 |
| `server/parser/structured_llm/client_factory.py` | 修改：新增 anthropic 分支 + `_create_anthropic_client()` |
| `server/parser/structured_llm/invoker.py` | 修改：扩展 `_is_retryable` |
| `server/pyproject.toml` | 修改：新增 `anthropic` 依赖（由 uv 自动管理） |
| `server/tests/core/parser_workflow/test_anthropic_provider.py` | 新建：anthropic provider 单元测试 |

---

## Task 1: 安装 anthropic 依赖

**Files:**
- Modify: `server/pyproject.toml`（uv 自动）

- [ ] **Step 1: 安装依赖**

```bash
cd server && uv add anthropic
```

Expected output: 类似 `Added anthropic>=0.x.x to dependencies`

- [ ] **Step 2: 验证可导入**

```bash
cd server && uv run python -c "import anthropic; print(anthropic.__version__)"
```

Expected: 打印版本号，无报错

- [ ] **Step 3: Commit**

```bash
git add server/pyproject.toml server/uv.lock
git commit -m "chore: add anthropic SDK dependency"
```

---

## Task 2: 新增配置字段（TDD）

**Files:**
- Modify: `server/config.py`
- Test: `server/tests/core/parser_workflow/test_anthropic_provider.py`

- [ ] **Step 1: 写失败测试**

新建 `server/tests/core/parser_workflow/test_anthropic_provider.py`：

```python
"""anthropic provider 单元测试。"""
from __future__ import annotations

from config import Settings


def test_anthropic_config_defaults():
    """ANTHROPIC_API_KEY 和 ANTHROPIC_BASE_URL 默认为空字符串。"""
    s = Settings()
    assert s.ANTHROPIC_API_KEY == ""
    assert s.ANTHROPIC_BASE_URL == ""
```

- [ ] **Step 2: 运行确认失败**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py::test_anthropic_config_defaults -v
```

Expected: `FAILED` — `AttributeError: 'Settings' object has no attribute 'ANTHROPIC_API_KEY'`

- [ ] **Step 3: 在 config.py 新增字段**

在 `server/config.py` 的 `LLM_API_KEY` / `LLM_BASE_URL` 段之后（约第 27 行）加入：

```python
    # ── Anthropic 专用凭证（MiniMax Anthropic-compatible endpoint）─────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = ""  # 如 https://api.minimax.chat/v1
```

- [ ] **Step 4: 运行确认通过**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py::test_anthropic_config_defaults -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add server/config.py server/tests/core/parser_workflow/test_anthropic_provider.py
git commit -m "feat: add ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL config fields"
```

---

## Task 3: 实现 `_create_anthropic_client()`（TDD）

**Files:**
- Modify: `server/parser/structured_llm/client_factory.py`
- Test: `server/tests/core/parser_workflow/test_anthropic_provider.py`

- [ ] **Step 1: 写失败测试（tool definition 生成）**

在 `test_anthropic_provider.py` 末尾追加：

```python
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from parser.structured_llm.client_factory import get_structured_client
from parser.structured_llm.errors import StructuredOutputError


class _DummyOutput(BaseModel):
    label: str
    score: float


def _make_tool_use_response(data: dict) -> MagicMock:
    """构造 anthropic messages.create 返回值，包含一个 tool_use block。"""
    block = MagicMock()
    block.type = "tool_use"
    block.input = data
    response = MagicMock()
    response.content = [block]
    return response


def test_anthropic_client_calls_messages_create():
    """get_structured_client('anthropic') 返回 callable，调用时走 messages.create。"""
    mock_anthropic_cls = MagicMock()
    mock_client_instance = MagicMock()
    mock_anthropic_cls.return_value = mock_client_instance
    mock_client_instance.messages.create.return_value = _make_tool_use_response(
        {"label": "foo", "score": 0.9}
    )

    with patch("parser.structured_llm.client_factory.anthropic") as mock_anthropic_mod:
        mock_anthropic_mod.Anthropic.return_value = mock_client_instance
        create_fn = get_structured_client("anthropic", "MiniMax-Text-01")
        result = create_fn(
            model="MiniMax-Text-01",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert isinstance(result, _DummyOutput)
    assert result.label == "foo"
    assert result.score == 0.9
    mock_client_instance.messages.create.assert_called_once()
```

- [ ] **Step 2: 运行确认失败**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py::test_anthropic_client_calls_messages_create -v
```

Expected: `FAILED` — `ValueError: 未知 provider: 'anthropic'`

- [ ] **Step 3: 在 client_factory.py 顶部导入 anthropic**

在 `server/parser/structured_llm/client_factory.py` 的 import 区域（第 1 行 `from __future__` 之后）加入：

```python
import anthropic
```

- [ ] **Step 4: 新增 `_create_anthropic_client()` 函数**

在 `client_factory.py` 的 `_create_openai_client()` 函数之后、`get_structured_client()` 之前插入：

```python
def _create_anthropic_client(
    api_key: str,
    base_url: str | None,
) -> Callable[..., BaseModel]:
    """通过 Anthropic SDK + tool use 创建结构化输出 callable。"""
    from parser.structured_llm.errors import StructuredOutputError

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
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=temperature,
            tools=[tool_def],
            tool_choice={"type": "tool", "name": tool_name},
            messages=messages,
            timeout=float(timeout or settings.PARSER_STRUCTURED_TIMEOUT_SECONDS),
        )
        for block in response.content:
            if block.type == "tool_use":
                return response_model(**block.input)
        raise StructuredOutputError(
            "Anthropic 响应中未找到 tool_use block",
            provider="anthropic",
            model=model,
            node_name="unknown",
            response_model=tool_name,
            retry_count=0,
            raw_error=repr(response.content),
        )

    return _create
```

- [ ] **Step 5: 在 `get_structured_client()` 新增 anthropic 分支**

在 `get_structured_client()` 的 `elif provider == "ollama":` 块之后、`else: raise ValueError` 之前插入：

```python
    elif provider == "anthropic":
        client = _create_anthropic_client(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL or None,
        )
        # anthropic provider 直接返回 client（已是 callable）
        return client
```

注意：此分支不能沿用下方 `def _create(...)` 闭包，因为 `_create_anthropic_client` 自己已经返回 callable，直接 return。需要调整 `get_structured_client` 结构，将现有 openai/dashscope/ollama 共享的 `def _create(...)` 闭包和 `return _create` 只在那三个分支执行。修改后的整体结构：

```python
def get_structured_client(provider: str, model: str) -> Callable[..., BaseModel]:
    if provider == "openai":
        client = _create_openai_client(
            model_ref=f"openai/{model}",
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL or None,
        )
    elif provider == "dashscope":
        client = _create_openai_client(
            model_ref=f"openai/{model}",
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
        )
    elif provider == "ollama":
        client = _create_openai_client(
            model_ref=f"ollama/{model}",
            api_key="ollama",
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
            "extra_body": extra_body,
            **kwargs,
        }
        return client.chat.completions.create(**create_kwargs)

    return _create
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py::test_anthropic_client_calls_messages_create -v
```

Expected: `PASSED`

- [ ] **Step 7: 补充 tool_use block 缺失时抛 StructuredOutputError 的测试**

在 `test_anthropic_provider.py` 末尾追加：

```python
def test_anthropic_client_raises_when_no_tool_use_block():
    """响应中无 tool_use block 时抛 StructuredOutputError。"""
    mock_client_instance = MagicMock()
    # 返回一个没有 tool_use 的 content（如只有 text block）
    text_block = MagicMock()
    text_block.type = "text"
    mock_response = MagicMock()
    mock_response.content = [text_block]
    mock_client_instance.messages.create.return_value = mock_response

    with patch("parser.structured_llm.client_factory.anthropic") as mock_anthropic_mod:
        mock_anthropic_mod.Anthropic.return_value = mock_client_instance
        create_fn = get_structured_client("anthropic", "MiniMax-Text-01")
        with pytest.raises(StructuredOutputError) as exc_info:
            create_fn(
                model="MiniMax-Text-01",
                messages=[{"role": "user", "content": "test"}],
                response_model=_DummyOutput,
            )
    assert "tool_use block" in str(exc_info.value)
```

- [ ] **Step 8: 运行测试确认通过**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -v
```

Expected: 所有 3 个测试 `PASSED`

- [ ] **Step 9: Commit**

```bash
git add server/parser/structured_llm/client_factory.py server/tests/core/parser_workflow/test_anthropic_provider.py
git commit -m "feat: add anthropic provider with tool use structured output"
```

---

## Task 4: 扩展 `_is_retryable` 支持 Anthropic 异常（TDD）

**Files:**
- Modify: `server/parser/structured_llm/invoker.py`
- Test: `server/tests/core/parser_workflow/test_anthropic_provider.py`

- [ ] **Step 1: 写失败测试（anthropic 超时可重试）**

在 `test_anthropic_provider.py` 末尾追加：

```python
from parser.structured_llm import invoke_structured


def test_invoke_structured_anthropic_timeout_retries():
    """anthropic.APITimeoutError 可重试，达到上限后抛 StructuredOutputError。"""
    import anthropic as anthropic_sdk

    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise anthropic_sdk.APITimeoutError(request=MagicMock())

    with patch(
        "parser.structured_llm.invoker.get_structured_client",
        return_value=_fake_create,
    ):
        with pytest.raises(StructuredOutputError) as exc_info:
            invoke_structured(
                node_name="classify_node",
                prompt="test",
                response_model=_DummyOutput,
                provider="anthropic",
                model="MiniMax-Text-01",
                max_retries=2,
            )
        assert exc_info.value.retry_count == 3

    assert call_count == 3


def test_invoke_structured_anthropic_internal_server_error_retries():
    """anthropic.InternalServerError（500）可重试。"""
    import anthropic as anthropic_sdk

    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise anthropic_sdk.InternalServerError(
            message="internal error",
            response=MagicMock(status_code=500),
            body={},
        )

    with patch(
        "parser.structured_llm.invoker.get_structured_client",
        return_value=_fake_create,
    ):
        with pytest.raises(StructuredOutputError):
            invoke_structured(
                node_name="classify_node",
                prompt="test",
                response_model=_DummyOutput,
                provider="anthropic",
                model="MiniMax-Text-01",
                max_retries=1,
            )

    assert call_count == 2


def test_invoke_structured_anthropic_auth_error_no_retry():
    """anthropic.AuthenticationError 不可重试，直接抛出。"""
    import anthropic as anthropic_sdk

    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise anthropic_sdk.AuthenticationError(
            message="invalid api key",
            response=MagicMock(status_code=401),
            body={},
        )

    with patch(
        "parser.structured_llm.invoker.get_structured_client",
        return_value=_fake_create,
    ):
        with pytest.raises(anthropic_sdk.AuthenticationError):
            invoke_structured(
                node_name="classify_node",
                prompt="test",
                response_model=_DummyOutput,
                provider="anthropic",
                model="MiniMax-Text-01",
                max_retries=2,
            )

    assert call_count == 1  # 不重试
```

- [ ] **Step 2: 运行确认失败**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py::test_invoke_structured_anthropic_timeout_retries tests/core/parser_workflow/test_anthropic_provider.py::test_invoke_structured_anthropic_auth_error_no_retry -v
```

Expected: `FAILED` — anthropic 异常未被识别为可重试/不可重试

- [ ] **Step 3: 修改 invoker.py 扩展 _is_retryable**

在 `invoker.py` 顶部（`from __future__ import annotations` 之后）新增导入：

```python
try:
    import anthropic as _anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _anthropic = None  # type: ignore
    _ANTHROPIC_AVAILABLE = False
```

在 `invoker.py` 的 `_is_retryable` 判断块（约第 168 行）中，将现有：

```python
            _is_retryable = (
                isinstance(e, TimeoutError)
                or isinstance(e, ConnectionError)
                or type(e).__name__ in (
                    "ReadTimeout",
                    "ConnectTimeout",
                    "ConnectError",
                    "PoolTimeout",
                    "WriteTimeout",
                    "APITimeoutError",
                    "RequestTimeoutError",
                    "Timeout",
                )
                or "timeout" in type(e).__name__.lower()
                or "timed out" in str(e).lower()
                or getattr(e, "status_code", 0) >= 500
            )
```

替换为：

```python
            # anthropic SDK 异常的显式判断
            _is_anthropic_retryable = False
            _is_anthropic_non_retryable = False
            if _ANTHROPIC_AVAILABLE and _anthropic is not None:
                if isinstance(e, (_anthropic.APITimeoutError, _anthropic.APIConnectionError)):
                    _is_anthropic_retryable = True
                elif isinstance(e, _anthropic.RateLimitError):
                    _is_anthropic_retryable = True
                elif isinstance(e, _anthropic.InternalServerError):
                    _is_anthropic_retryable = True
                elif isinstance(e, (_anthropic.AuthenticationError, _anthropic.BadRequestError)):
                    _is_anthropic_non_retryable = True

            if _is_anthropic_non_retryable:
                _logger.error(
                    "structured_llm_anthropic_non_retryable",
                    node_name=node_name,
                    provider=resolved_provider,
                    model=resolved_model,
                    error=str(e),
                )
                raise e

            _is_retryable = (
                _is_anthropic_retryable
                or isinstance(e, TimeoutError)
                or isinstance(e, ConnectionError)
                or type(e).__name__ in (
                    "ReadTimeout",
                    "ConnectTimeout",
                    "ConnectError",
                    "PoolTimeout",
                    "WriteTimeout",
                    "APITimeoutError",
                    "RequestTimeoutError",
                    "Timeout",
                )
                or "timeout" in type(e).__name__.lower()
                or "timed out" in str(e).lower()
                or getattr(e, "status_code", 0) >= 500
            )
```

- [ ] **Step 4: 运行全部 anthropic 测试确认通过**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -v
```

Expected: 所有测试 `PASSED`

- [ ] **Step 5: 运行已有测试确认无回归**

```bash
cd server && uv run pytest tests/core/parser_workflow/ -v --ignore=tests/core/parser_workflow/test_classify_node_real_llm.py --ignore=tests/core/parser_workflow/test_escalate_node_real_llm.py --ignore=tests/core/parser_workflow/test_structure_node_real_llm.py --ignore=tests/core/parser_workflow/test_transform_node_real_llm.py --ignore=tests/core/parser_workflow/test_parse_node_real.py --ignore=tests/core/parser_workflow/test_slice_node_real.py
```

Expected: 无新增失败

- [ ] **Step 6: Commit**

```bash
git add server/parser/structured_llm/invoker.py server/tests/core/parser_workflow/test_anthropic_provider.py
git commit -m "feat: extend invoker _is_retryable to handle anthropic SDK exceptions"
```

---

## Task 5: 更新错误文案 + 验证 unknown provider 报错

**Files:**
- Test: `server/tests/core/parser_workflow/test_anthropic_provider.py`

- [ ] **Step 1: 写测试确认 unknown provider 报错包含 anthropic**

在 `test_anthropic_provider.py` 末尾追加：

```python
def test_get_structured_client_unknown_provider_raises():
    """未知 provider 抛 ValueError，提示包含 anthropic。"""
    with pytest.raises(ValueError) as exc_info:
        get_structured_client("unknown_provider", "some-model")
    assert "anthropic" in str(exc_info.value)
```

- [ ] **Step 2: 运行确认通过（Task 3 Step 5 已更新错误文案）**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py::test_get_structured_client_unknown_provider_raises -v
```

Expected: `PASSED`

- [ ] **Step 3: 运行全套测试最终确认**

```bash
cd server && uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -v
```

Expected: 所有测试 `PASSED`

- [ ] **Step 4: Final commit**

```bash
git add server/tests/core/parser_workflow/test_anthropic_provider.py
git commit -m "test: add unknown provider validation test for anthropic provider"
```
