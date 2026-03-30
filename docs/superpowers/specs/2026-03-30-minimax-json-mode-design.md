---
title: MiniMax-M2.7 JSON system prompt 模式替换 tool_use
date: 2026-03-30
status: approved
---

## 背景

当前 `client_factory.py` 使用 Anthropic SDK streaming tool_use 方式获取结构化输出：通过 `tool_choice` 强制模型调用工具，收集 `InputJSONDelta.partial_json` 拼合 JSON。

MiniMax-M2.7 是思考型模型，通过 Anthropic-compatible API 调用时不输出 `InputJSONDelta`，而是输出：

1. `ThinkingDelta` × N（推理过程）
2. `SignatureDelta` × 1
3. `TextDelta` × N（普通文本答案，非 JSON）

导致 `partial_count=0`，fallback 尝试将普通文本解析为 JSON 失败，报 `transform_segment_llm_failed_fallback` 错误。

## 目标

- 替换为 JSON system prompt 模式，不依赖 tool_use
- 确保输出合法 JSON 且通过 Pydantic schema 校验
- JSON 解析失败时触发重试

## 变更范围

三个文件：`client_factory.py`、`errors.py`、`invoker.py`

---

## 设计

### 1. `client_factory.py` — JSON system prompt 模式

**移除：** `tools`、`tool_choice` 参数

**新增：** 在 `messages` 列表首位注入 system message：
```
你是结构化数据提取助手。严格按以下 JSON Schema 输出，只返回 JSON 对象，不包含任何解释或 Markdown 代码块。

Schema:
{schema}
```
schema 由 `response_model.model_json_schema()` 生成，`json.dumps` 格式化为字符串。

**事件收集：** 只收集 `TextDelta`，跳过 `ThinkingDelta` / `SignatureDelta`。

**解析管道（按顺序）：**
1. `json.loads(text.strip())` — 直接解析
2. 提取 ` ```json ... ``` ` 块后解析
3. 提取文本中第一个完整 `{...}` 或 `[...]` 后解析
4. 全部失败 → 抛 `JsonOutputParseError`

**校验：** `response_model.model_validate(parsed_dict)` — Pydantic 校验失败抛 `ValidationError`（非重试）。

---

### 2. `errors.py` — 新增 `JsonOutputParseError`

```python
class JsonOutputParseError(RuntimeError):
    """模型输出无法解析为合法 JSON，可触发重试。"""
```

---

### 3. `invoker.py` — 将 `JsonOutputParseError` 纳入可重试

在 `_is_retryable` 判断中增加：
```python
or isinstance(e, JsonOutputParseError)
```

**重试行为：**

| 错误类型 | 行为 |
|---------|------|
| `JsonOutputParseError` | 可重试，最多 `max_retries` 次 |
| `PydanticValidationError` | 不重试，直接抛 `StructuredOutputError` |
| 网络/超时错误 | 可重试（现有行为） |
| `AuthenticationError` / `BadRequestError` | 不重试（现有行为） |

---

## 不在本次范围内

- 支持真正的 Anthropic Claude 模型（当前仅支持 MiniMax-M2.7）
- 修改 prompt 模板（system message 格式后续可调整）
- 修改 retry 次数配置
