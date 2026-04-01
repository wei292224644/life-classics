# LLM 迁移清理设计

## 背景

之前已将 `workflow_parser_kb` 中的 LLM 调用逻辑迁移到 `server/llm/`，但保留了部分保守操作：
- `workflow_parser_kb/llm.py` 中的 `resolve_provider()` 未被使用（死代码）
- `invoker.py` 与 `structured_gateway.py` 逻辑重复
- `structured_llm/__init__.py` 仅重新导出，无实际作用
- `client_factory.py` 仍直接调用 Anthropic SDK，未使用 `server/llm/`

测试已通过，现在需要完成迁移清理。

## 目标架构

```
workflow_product_analysis/
  └─ nodes.py / ingredient_parser.py
       └─ client_factory.get_structured_client() [重构]
            └─ llm.anthropic.create_structured() [server/llm/]

workflow_parser_kb/nodes/
  └─ classify_node / escalate_node / structure_node / transform_node
       └─ structured_gateway.invoke_structured()
            └─ llm.anthropic.create_structured() [server/llm/]

errors.py [保留]
  └─ StructuredOutputError, JsonOutputParseError
```

## 改动内容

### 1. 删除死代码

| 文件 | 操作 |
|------|------|
| `workflow_parser_kb/llm.py` | 删除 - `resolve_provider()` 无任何导入 |
| `invoker.py` | 删除 - 与 structured_gateway 重复，nodes 不使用 |
| `structured_llm/__init__.py` | 删除 - 仅重新导出 |

### 2. 重构 client_factory.py

`client_factory.py` 仍被 `workflow_product_analysis/` 使用，需要改用 `server/llm/anthropic.create_structured()`：

```python
# 重构前
from anthropic import Anthropic
def _create_anthropic_client(api_key, base_url):
    client = Anthropic(api_key=api_key, base_url=base_url)
    def _create(...):
        # 直接调用 client.messages.create()
        ...
    return _create

# 重构后
from llm.anthropic import create_structured as _create_structured_anthro
def get_structured_client(provider: str, model: str):
    if provider == "anthropic":
        return _create_structured_anthro()
    else:
        raise ValueError(...)
```

### 3. 保留的文件

- `errors.py` - `StructuredOutputError`、`JsonOutputParseError` 被 `structured_gateway` 和 tests 使用
- `structured_gateway.py` - 已正确使用 `server/llm/`，无需修改
- `client_factory.py` - 重构为使用 `server/llm/`

### 4. 测试文件更新

Tests 中对 `structured_llm/__init__.py` 的导入需改为直接导入 `errors`：
- `test_structure_node.py`
- `test_transform_node.py`
- `test_classify_node_fallback.py`
- `test_escalate_node.py`

## 实施步骤

1. 检查 `workflow_parser_kb/llm.py` 确认无任何外部导入
2. 删除 `workflow_parser_kb/llm.py`
3. 删除 `invoker.py`
4. 删除 `structured_llm/__init__.py`
5. 重构 `client_factory.py` 使用 `server/llm/`
6. 更新 tests 的 imports
7. 运行测试验证

## 风险评估

- **低风险**：`workflow_parser_kb/llm.py` 确认无导入，删除安全
- **低风险**：`invoker.py` 与 `structured_gateway.py` 重复确认，nodes 不使用
- **中风险**：`structured_llm/__init__.py` 删除后需更新 tests 导入

## 验收标准

- `workflow_product_analysis/` 仍正常工作
- `workflow_parser_kb/nodes/` 仍正常工作
- 所有 tests 通过