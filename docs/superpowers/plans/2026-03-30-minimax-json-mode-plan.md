# MiniMax-M2.7 JSON System Prompt 模式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `client_factory.py` 的结构化输出从 Anthropic tool_use 模式替换为 JSON system prompt 模式，使 MiniMax-M2.7 能正确返回并解析结构化 JSON，并在解析失败时触发重试。

**Architecture:** 移除 `tools` / `tool_choice`，改为在 `system` 参数中注入 JSON Schema 指令；收集 `TextDelta` 并经三步解析管道提取 JSON；新增 `JsonOutputParseError` 异常类，在 `invoker.py` 重试循环中纳入可重试列表。

**Tech Stack:** Python 3.12, Pydantic v2, Anthropic SDK, pytest, unittest.mock

---

## 文件变更表

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `server/parser/structured_llm/errors.py` | 新增 `JsonOutputParseError` |
| 修改 | `server/parser/structured_llm/client_factory.py` | 替换 tool_use 为 JSON system prompt 模式 |
| 修改 | `server/parser/structured_llm/invoker.py` | 将 `JsonOutputParseError` 纳入可重试 |
| 修改 | `server/tests/core/parser_workflow/test_anthropic_provider.py` | 更新/新增测试 |

---

## Task 1: 新增 `JsonOutputParseError` 异常类

**Files:**
- Modify: `server/parser/structured_llm/errors.py`
- Test: `server/tests/core/parser_workflow/test_anthropic_provider.py`

- [ ] **Step 1: 写失败测试**

在 `test_anthropic_provider.py` 末尾追加：

```python
def test_json_output_parse_error_is_importable_and_is_runtime_error():
    """JsonOutputParseError 可从 errors 模块导入，且是 RuntimeError 子类。"""
    from parser.structured_llm.errors import JsonOutputParseError
    err = JsonOutputParseError("test message")
    assert isinstance(err, RuntimeError)
    assert "test message" in str(err)
```

- [ ] **Step 2: 运行确认失败**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py::test_json_output_parse_error_is_importable_and_is_runtime_error -v
```

预期：`FAILED` — `ImportError: cannot import name 'JsonOutputParseError'`

- [ ] **Step 3: 在 `errors.py` 新增异常类**

在 `StructuredOutputError` 类定义之后追加：

```python
class JsonOutputParseError(RuntimeError):
    """模型输出无法解析为合法 JSON，可触发重试。"""
```

- [ ] **Step 4: 运行确认通过**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py::test_json_output_parse_error_is_importable_and_is_runtime_error -v
```

预期：`PASSED`

- [ ] **Step 5: 提交**

```bash
git add server/parser/structured_llm/errors.py server/tests/core/parser_workflow/test_anthropic_provider.py
git commit -m "feat: add JsonOutputParseError for retryable JSON parse failures"
```

---

## Task 2: 为新 `client_factory.py` 行为编写测试（先写测试，后实现）

**Files:**
- Test: `server/tests/core/parser_workflow/test_anthropic_provider.py`

- [ ] **Step 1: 在测试文件顶部添加新 import**

在 `test_anthropic_provider.py` 文件顶部的 import 区域添加（找到 `from parser.structured_llm.errors import StructuredOutputError` 这行，在其后追加）：

```python
from parser.structured_llm.errors import JsonOutputParseError
```

- [ ] **Step 2: 添加新的 streaming TextDelta mock helper**

在文件中的 `_make_streaming_text_only_response` 函数定义之后，追加以下 helper：

```python
def _make_streaming_text_response(text: str) -> MagicMock:
    """构造返回指定文本内容的 TextDelta streaming 响应。"""

    class _MockTextDelta:
        def __init__(self, content: str):
            self.text = content

    class _MockContentBlockDeltaEvent:
        def __init__(self, content: str):
            self.type = "content_block_delta"
            self.delta = _MockTextDelta(content)

    class _MockMessageStopEvent:
        type = "message_stop"

    class _MockStream:
        def __init__(self, content: str):
            self._content = content

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            yield _MockContentBlockDeltaEvent(self._content)
            yield _MockMessageStopEvent()

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _MockStream(text)
    return mock_client
```

- [ ] **Step 3: 添加 6 个新测试**

在文件末尾追加以下测试（全部替换现有的 `test_anthropic_client_calls_messages_create` 和 `test_anthropic_client_raises_when_no_tool_use_block` 的期望——不要删除这两个旧测试，只追加新测试）：

```python
def test_json_mode_no_tools_in_request():
    """JSON system prompt 模式不传 tools / tool_choice 参数。"""
    mock_client = _make_streaming_text_response('{"label": "foo", "score": 0.9}')

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs


def test_json_mode_system_contains_schema():
    """create 调用包含 system 参数，且内容包含 response_model 的字段名。"""
    mock_client = _make_streaming_text_response('{"label": "foo", "score": 0.9}')

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "system" in call_kwargs
    # schema 中应包含字段名
    assert "label" in call_kwargs["system"]
    assert "score" in call_kwargs["system"]


def test_json_mode_direct_json_response():
    """模型直接返回裸 JSON 时，正确解析为 response_model。"""
    mock_client = _make_streaming_text_response('{"label": "foo", "score": 0.9}')

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        result = create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert isinstance(result, _DummyOutput)
    assert result.label == "foo"
    assert result.score == 0.9


def test_json_mode_markdown_block_response():
    """模型返回 ```json ... ``` 包裹时，提取后正确解析。"""
    text = '```json\n{"label": "bar", "score": 0.5}\n```'
    mock_client = _make_streaming_text_response(text)

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        result = create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert result.label == "bar"
    assert result.score == 0.5


def test_json_mode_json_embedded_in_text():
    """模型返回文字中嵌入 JSON 对象时，提取后正确解析。"""
    text = '好的，结果如下：{"label": "baz", "score": 0.3} 以上是结果。'
    mock_client = _make_streaming_text_response(text)

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        result = create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert result.label == "baz"
    assert result.score == 0.3


def test_json_mode_invalid_json_raises_parse_error():
    """模型返回无法解析的文本时，抛 JsonOutputParseError。"""
    mock_client = _make_streaming_text_response("这是普通文本，完全没有 JSON 内容")

    with patch("parser.structured_llm.client_factory.anthropic") as mock_mod:
        mock_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        with pytest.raises(JsonOutputParseError):
            create_fn(
                model="MiniMax-M2.7",
                messages=[{"role": "user", "content": "test"}],
                response_model=_DummyOutput,
            )
```

- [ ] **Step 4: 运行 6 个新测试，确认全部失败**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -k "json_mode" -v
```

预期：6 个 `FAILED`（实现尚未更新）

- [ ] **Step 5: 提交**

```bash
git add server/tests/core/parser_workflow/test_anthropic_provider.py
git commit -m "test: add failing tests for JSON system prompt mode in client_factory"
```

---

## Task 3: 重写 `client_factory.py` 为 JSON system prompt 模式

**Files:**
- Modify: `server/parser/structured_llm/client_factory.py`

- [ ] **Step 1: 完整替换 `client_factory.py`**

将文件内容替换为：

```python
"""按 provider 构建结构化输出客户端（仅 anthropic）。"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

import anthropic
import structlog
from pydantic import BaseModel

from config import settings
from parser.structured_llm.errors import JsonOutputParseError

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
```

- [ ] **Step 2: 运行新测试，确认 6 个通过**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -k "json_mode" -v
```

预期：6 个 `PASSED`

- [ ] **Step 3: 运行旧测试，确认已知失败的两个**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -v
```

预期：
- `test_anthropic_client_calls_messages_create` — `FAILED`（断言 `tool_choice` / `tools` 已不存在）
- `test_anthropic_client_raises_when_no_tool_use_block` — `FAILED`（现在抛 `JsonOutputParseError` 不是 `ValueError`，且错误信息变了）
- 其余测试 `PASSED`

- [ ] **Step 4: 更新两个旧测试以匹配新行为**

找到 `test_anthropic_client_calls_messages_create`，将其完整替换为：

```python
def test_anthropic_client_calls_messages_create():
    """get_structured_client('anthropic') 返回 callable，调用时走 streaming messages.create，使用 JSON system prompt 模式。"""
    mock_client = _make_streaming_text_response('{"label": "foo", "score": 0.9}')

    with patch("parser.structured_llm.client_factory.anthropic") as mock_anthropic_mod:
        mock_anthropic_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        result = create_fn(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "test"}],
            response_model=_DummyOutput,
        )

    assert isinstance(result, _DummyOutput)
    assert result.label == "foo"
    assert result.score == 0.9
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "system" in call_kwargs
    assert call_kwargs["stream"] is True
    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs
```

找到 `test_anthropic_client_raises_when_no_tool_use_block`，将其完整替换为：

```python
def test_anthropic_client_raises_when_no_parseable_json():
    """响应中无可解析的 JSON 时抛 JsonOutputParseError。"""
    mock_client = _make_streaming_text_response("这是普通文本，完全没有 JSON")

    with patch("parser.structured_llm.client_factory.anthropic") as mock_anthropic_mod:
        mock_anthropic_mod.Anthropic.return_value = mock_client
        create_fn = get_structured_client("anthropic", "MiniMax-M2.7")
        with pytest.raises(JsonOutputParseError):
            create_fn(
                model="MiniMax-M2.7",
                messages=[{"role": "user", "content": "test"}],
                response_model=_DummyOutput,
            )
```

- [ ] **Step 5: 运行全部测试，确认全部通过**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -v
```

预期：全部 `PASSED`（注意：`_make_streaming_tool_use_response` 和 `_make_streaming_text_only_response` 两个 helper 在新测试中不再使用，但保留不删除也不影响测试结果）

- [ ] **Step 6: 提交**

```bash
git add server/parser/structured_llm/client_factory.py server/tests/core/parser_workflow/test_anthropic_provider.py
git commit -m "feat: replace tool_use with JSON system prompt mode for MiniMax-M2.7"
```

---

## Task 4: 将 `JsonOutputParseError` 纳入 `invoker.py` 可重试列表

**Files:**
- Modify: `server/parser/structured_llm/invoker.py`
- Test: `server/tests/core/parser_workflow/test_anthropic_provider.py`

- [ ] **Step 1: 写失败测试**

在 `test_anthropic_provider.py` 末尾追加：

```python
def test_invoke_structured_json_parse_error_retries():
    """JsonOutputParseError 可重试，达上限后抛 StructuredOutputError。"""
    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise JsonOutputParseError("JSON 解析失败")

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
                model="MiniMax-M2.7",
                max_retries=2,
            )
        assert exc_info.value.retry_count == 3

    assert call_count == 3  # 首次 + 2 次重试


def test_invoke_structured_json_parse_error_single_retry():
    """JsonOutputParseError max_retries=0 时不重试，直接抛 StructuredOutputError。"""
    call_count = 0

    def _fake_create(*, model, messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise JsonOutputParseError("JSON 解析失败")

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
                model="MiniMax-M2.7",
                max_retries=0,
            )

    assert call_count == 1
```

- [ ] **Step 2: 运行确认失败**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -k "json_parse_error_retries or json_parse_error_single" -v
```

预期：2 个 `FAILED` — `JsonOutputParseError` 目前不被重试，`call_count` 为 1

- [ ] **Step 3: 在 `invoker.py` 添加 `JsonOutputParseError` import 并纳入重试**

在 `invoker.py` 顶部 import 区域，找到：

```python
from parser.structured_llm.errors import StructuredOutputError
```

替换为：

```python
from parser.structured_llm.errors import JsonOutputParseError, StructuredOutputError
```

在 `_is_retryable` 判断块（约第 198 行）中，找到：

```python
            _is_retryable = (
                _is_anthropic_retryable
                or isinstance(e, TimeoutError)
```

替换为：

```python
            _is_retryable = (
                _is_anthropic_retryable
                or isinstance(e, JsonOutputParseError)
                or isinstance(e, TimeoutError)
```

- [ ] **Step 4: 运行确认通过**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -k "json_parse_error_retries or json_parse_error_single" -v
```

预期：2 个 `PASSED`

- [ ] **Step 5: 运行全部 anthropic provider 测试**

```bash
cd server
uv run pytest tests/core/parser_workflow/test_anthropic_provider.py -v
```

预期：全部 `PASSED`

- [ ] **Step 6: 运行整个 parser_workflow 测试套件**

```bash
cd server
uv run pytest tests/core/parser_workflow/ -v
```

预期：全部 `PASSED`

- [ ] **Step 7: 提交**

```bash
git add server/parser/structured_llm/invoker.py server/tests/core/parser_workflow/test_anthropic_provider.py
git commit -m "feat: make JsonOutputParseError retryable in invoke_structured"
```

---

## 自检

**Spec coverage：**
- ✅ 移除 tools / tool_choice → Task 3
- ✅ system 参数注入 JSON Schema → Task 3
- ✅ TextDelta 收集，跳过 ThinkingDelta → Task 3
- ✅ 三步解析管道（直接/markdown/regex）→ Task 3
- ✅ JsonOutputParseError 新异常 → Task 1
- ✅ JSON 解析失败触发重试 → Task 4
- ✅ Pydantic 校验失败不重试（现有行为，model_validate 抛 ValidationError，invoker.py 不变）→ 无需修改

**Placeholder 扫描：** 无 TBD / TODO

**类型一致性：**
- `JsonOutputParseError` 在 Task 1 定义，Task 2/3/4 均正确引用
- `model_validate` 在 Task 3 中使用（Pydantic v2 API，项目已用 v2）
- `_make_streaming_text_response` 在 Task 2 定义，Task 3 中复用
