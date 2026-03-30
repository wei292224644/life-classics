# 替换 instructor：改用 Anthropic SDK + Tool Use 实现结构化输出

**日期**：2026-03-30
**状态**：已批准，待实施

## 背景

当前 `server/parser/structured_llm/` 使用 `instructor` 库（JSON mode）包装 OpenAI-compatible 客户端调用 MiniMax 2.7 模型。存在以下问题：

- 模型频繁返回 timeout 或 500 错误，单次请求可达 60s+
- instructor JSON mode 与 MiniMax 2.7 兼容性差，JSON 解析失败率高
- MiniMax 2.7 官方推荐通过 Anthropic API 接入，并对 tool use 做了优化

**目标**：在 `structured_llm/` 模块内新增 `anthropic` provider，使用 Anthropic SDK + tool use 实现结构化输出，对上层 nodes 完全透明，不影响现有 openai/dashscope/ollama provider。

---

## 一、配置层（`server/config.py`）

新增两个配置字段：

```python
ANTHROPIC_API_KEY: str = ""
ANTHROPIC_BASE_URL: str = ""  # MiniMax Anthropic-compatible endpoint
```

`PARSER_LLM_PROVIDER` 及各节点级 provider 字段（`CLASSIFY_LLM_PROVIDER` 等）新增合法值 `anthropic`。

`.env` 配置示例：

```
ANTHROPIC_API_KEY=your_minimax_key
ANTHROPIC_BASE_URL=https://api.minimax.chat/v1
PARSER_LLM_PROVIDER=anthropic
CLASSIFY_MODEL=MiniMax-Text-01
ESCALATE_MODEL=MiniMax-Text-01
DOC_TYPE_LLM_MODEL=MiniMax-Text-01
```

**约束**：不复用 `LLM_API_KEY`/`LLM_BASE_URL`，保持 openai provider 配置独立。

---

## 二、`structured_llm/client_factory.py` 改造

### 新增 `_create_anthropic_client()`

返回与现有 `_create()` 签名完全兼容的 callable：

```
(model, messages, response_model, temperature, timeout, extra_body, **kwargs) -> BaseModel
```

内部实现步骤：

1. `anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL)` 初始化客户端
2. 从 `response_model.model_json_schema()` 生成 tool definition：
   ```python
   tool = {
       "name": response_model.__name__,
       "description": f"返回结构化数据：{response_model.__name__}",
       "input_schema": response_model.model_json_schema(),
   }
   ```
3. 调用 `client.messages.create()`：
   ```python
   response = client.messages.create(
       model=model,
       max_tokens=4096,
       temperature=temperature,
       tools=[tool],
       tool_choice={"type": "tool", "name": response_model.__name__},
       messages=messages,
   )
   ```
4. 从 `response.content` 中找到 `type == "tool_use"` 的 block；若不存在，直接抛 `StructuredOutputError`（不重试）
5. `response_model(**block.input)` 校验并返回 Pydantic 实例

### `get_structured_client()` 新增分支

```python
elif provider == "anthropic":
    return _create_anthropic_client(
        model=model,
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL or None,
    )
```

### 依赖

```bash
cd server && uv add anthropic
```

instructor 暂时保留（openai/dashscope/ollama provider 仍依赖），后续可按需清理。

---

## 三、错误处理（`server/parser/structured_llm/invoker.py`）

`invoker.py` 的 `_is_retryable` 逻辑扩展，新增对 Anthropic SDK 异常的识别：

| 异常类型 | 处理方式 |
|---|---|
| `anthropic.APITimeoutError` | 可重试 |
| `anthropic.InternalServerError`（500） | 可重试 |
| `anthropic.RateLimitError`（429） | 可重试 |
| `anthropic.APIConnectionError` | 可重试 |
| `anthropic.AuthenticationError` | 不可重试，直接抛出 |
| `anthropic.BadRequestError` | 不可重试，直接抛出 |
| tool_use block 缺失 | 不可重试，抛 `StructuredOutputError` |
| Pydantic `ValidationError` | 不可重试，抛 `StructuredOutputError` |

重试次数、超时、日志、`StructuredOutputError` 包装逻辑均复用现有实现，无需改动。

---

## 已知限制

**Token 计数**：`invoker.py` 通过 `getattr(result, "usage", None)` 读取 token 用量，但 `_create_anthropic_client` 返回 Pydantic 实例（不携带 usage）。anthropic provider 的 token 指标将静默跳过，不影响功能，后续可扩展 callable 返回元组或将 usage 写入自定义属性来修复。

---

## 影响范围

| 文件 | 变更类型 |
|---|---|
| `server/config.py` | 新增 2 个字段 |
| `server/parser/structured_llm/client_factory.py` | 新增 anthropic 分支和 `_create_anthropic_client()` |
| `server/parser/structured_llm/invoker.py` | 扩展 `_is_retryable` 判断 |
| `server/pyproject.toml` | 新增 `anthropic` 依赖 |
| `server/.env`（本地） | 新增 `ANTHROPIC_API_KEY`、`ANTHROPIC_BASE_URL` |

**不变更**：`nodes/classify_node.py`、`nodes/structure_node.py`、其他 nodes、`invoker.py` 主体逻辑、openai/dashscope/ollama provider。

---

## 测试要点

- `client_factory.py` 单测：mock `anthropic.Anthropic`，验证 tool definition 生成、tool_use block 解析、Pydantic 校验
- `invoker.py` 单测：验证 anthropic 各异常类型的重试/不重试行为
- 集成测试：对 `classify_node` 用 anthropic provider 走一次完整流水线
