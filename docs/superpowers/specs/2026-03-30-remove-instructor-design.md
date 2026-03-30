# 删除 OpenAI + Instructor 结构化输出

## 背景

Parser Workflow 的结构化输出网关（`parser/structured_llm/`）此前通过 `instructor` 库对接 OpenAI-compatible API（dashscope、ollama、openai），同时 `anthropic` provider 已实现独立的流式 tool use。

项目决定统一到 **仅使用 anthropic provider**，删除 `instructor` 依赖及所有非 anthropic provider 组合。

## 变更范围

| 文件 | 变更内容 |
|------|----------|
| `pyproject.toml` | 删除 `instructor>=1.14.5` 依赖 |
| `parser/structured_llm/client_factory.py` | 删除 `import instructor`、删除 `_create_openai_client()`、删除 openai/dashscope/ollama 分支，只保留 anthropic |
| `parser/structured_llm/invoker.py` | `resolve_provider_for_node()` 硬编码兜底从 `"openai"` 改为 `"anthropic"` |
| `config.py` | 注释中删除 "(Instructor)" 字样 |
| `README.md` | 更新 instructor 相关文档描述 |

## 详细设计

### 1. `client_factory.py` 变更

**删除**：
```python
import instructor
```

**删除整个函数**：
```python
def _create_openai_client(model_ref, api_key, base_url, **extra_kwargs):
    return instructor.from_provider(
        model_ref, mode=instructor.Mode.JSON, api_key=api_key,
        base_url=base_url, timeout=settings.PARSER_STRUCTURED_TIMEOUT_SECONDS, **extra_kwargs
    )
```

**`get_structured_client()` 变更**：
- `openai` 分支 → 删除
- `dashscope` 分支 → 删除
- `ollama` 分支 → 删除
- `anthropic` 分支 → 保留（已是完整实现）
- 其他 provider → 抛 `ValueError`

### 2. `invoker.py` 变更

`resolve_provider_for_node()` 的兜底逻辑：

**变更前**：
```python
return "openai"  # 硬编码兜底
```

**变更后**：
```python
return "anthropic"  # 硬编码兜底
```

### 3. 配置说明

- `CLASSIFY_LLM_PROVIDER`、`ESCALATE_LLM_PROVIDER`、`TRANSFORM_LLM_PROVIDER`、`DOC_TYPE_LLM_PROVIDER` 配置项**保留**，但运行时仅接受 `anthropic` 值
- 若配置了其他 provider，`get_structured_client()` 抛 `ValueError`

### 4. 测试

- `tests/core/parser_workflow/test_structured_llm.py` 已是注释状态，无需修改
- `resolve_provider_for_node()` 兜底测试需更新断言（`"openai"` → `"anthropic"`），但该文件已是注释状态

## 实施步骤

1. 从 `pyproject.toml` 删除 `instructor` 依赖
2. 修改 `parser/structured_llm/client_factory.py`：
   - 删除 `import instructor`
   - 删除 `_create_openai_client()` 函数
   - 简化 `get_structured_client()` 只保留 anthropic
3. 修改 `parser/structured_llm/invoker.py`：`resolve_provider_for_node()` 兜底改为 `"anthropic"`
4. 更新 `config.py` 注释
5. 更新 `README.md` 文档
6. 运行 `uv sync` 更新锁文件
7. 运行测试验证

## 风险与注意事项

- 本次变更是**单向**的——删除后无法通过配置回退到 openai/dashscope/ollama provider
- 如后续需重新支持其他 provider，需重新引入 instructor 或其他结构化输出方案
