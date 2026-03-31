# config.py 配置合并设计

## 背景

当前 `server/config.py` 中的配置项随项目增长变得臃肿，特别是 LLM 模型相关配置分散在十几处：

- `CLASSIFY_MODEL` / `ESCALATE_MODEL` / `TRANSFORM_MODEL` / `DOC_TYPE_LLM_MODEL`
- `ANALYSIS_DEMOGRAPHICS_MODEL` / `ANALYSIS_SCENARIOS_MODEL` / `ANALYSIS_ADVICE_MODEL` / `ANALYSIS_VERDICT_MODEL`
- `PARSE_MODEL` / `CHAT_MODEL` / `INGREDIENT_ANALYSIS_MODEL`
- `PARSER_LLM_PROVIDER` / `ANALYSIS_LLM_PROVIDER` / `PARSE_LLM_PROVIDER` / `CHAT_PROVIDER`
- `EMBEDDING_LLM_PROVIDER`
- `DASHSCOPE_API_KEY` / `DASHSCOPE_BASE_URL` / `OLLAMA_BASE_URL`

经分析发现：
- **所有 LLM 调用均走 MiniMax 2.7**（Anthropic-compatible endpoint）
- **Embedding 独立走 Ollama** 部署的 `nomic-embed-text`
- 所有 LLM 模型（Parser / Analysis / Chat / Parse / IngredientAnalysis）均为同一模型

## 目标

将 **15+ 项模型配置 + 5 项 provider 配置** 简化为 **2 项**：
- `DEFAULT_MODEL` — 所有 LLM 调用统一模型
- `EMBEDDING_MODEL` — 向量嵌入模型

## config.py 改动

### 删除的配置项（共 20 项）

**模型配置（10 项）：**
```
CLASSIFY_MODEL
ESCALATE_MODEL
TRANSFORM_MODEL
DOC_TYPE_LLM_MODEL
ANALYSIS_DEMOGRAPHICS_MODEL
ANALYSIS_SCENARIOS_MODEL
ANALYSIS_ADVICE_MODEL
ANALYSIS_VERDICT_MODEL
PARSE_MODEL
CHAT_MODEL
INGREDIENT_ANALYSIS_MODEL
```

**Provider 配置（5 项）：**
```
PARSER_LLM_PROVIDER
ANALYSIS_LLM_PROVIDER
PARSE_LLM_PROVIDER
CHAT_PROVIDER
EMBEDDING_LLM_PROVIDER
```

**不再使用的连接配置（3 项）：**
```
DASHSCOPE_API_KEY
DASHSCOPE_BASE_URL
OLLAMA_BASE_URL
```

### 新增配置（2 项）

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_MODEL` | `MiniMax-2.7` | 所有 LLM 调用统一使用此模型 |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama 部署的嵌入模型 |

### 保留配置

| 配置 | 保留原因 |
|------|----------|
| `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` | MiniMax 连接凭证 |
| `LLM_API_KEY` / `LLM_BASE_URL` | OpenAI-compatible 备用连接 |
| `OLLAMA_BASE_URL` | 若 embedding 需从配置读取则保留 |

## 代码改动

### 1. `server/config.py`

```python
# 新增
DEFAULT_MODEL: str = "MiniMax-2.7"
EMBEDDING_MODEL: str = "nomic-embed-text"

# 删除所有 *MODEL 和 *PROVIDER 相关配置（见上方列表）
```

### 2. LLM 调用点修改

所有直接引用 `settings.ESCALATE_MODEL` 等配置的地方，改为统一使用 `settings.DEFAULT_MODEL`。

涉及文件（需全量搜索 `settings.` 确认）：
- `server/worflow_parser_kb/nodes/` — `classify_node`, `escalate_node`, `structure_node`, `transform_node`
- `server/worflow_parser_kb/llm.py` — `resolve_provider_for_node()` 及相关
- `server/workflow_product_analysis/nodes.py`
- `server/workflow_product_analysis/ingredient_parser.py`
- `server/agent/agent.py`
- `server/api/search/service.py`

### 3. `server/llm/` 清理

`resolve_provider_for_node()` 等 provider 路由逻辑不再需要，删除或简化为直接使用 `DEFAULT_MODEL`：

```python
# 简化后的逻辑
def get_default_model():
    return settings.DEFAULT_MODEL
```

### 4. `server/kb/embeddings.py`

确认 embedding 模型来源：
- 如果 Ollama 连接地址不再通过 `OLLAMA_BASE_URL` 配置，则需确认 `embeddings.py` 如何获取地址

## 实施步骤

1. 修改 `server/config.py`：新增 2 项，删除 20 项
2. 全量搜索 `settings.CLASSIFY_MODEL`、`settings.ESCALATE_MODEL` 等，确认所有引用点
3. 将所有引用点改为 `settings.DEFAULT_MODEL`
4. 删除 `server/llm/` 中 `resolve_provider_for_node()` 等无用逻辑
5. 确认 embedding 相关配置是否需要保留 `OLLAMA_BASE_URL`
6. 运行测试验证

## 风险评估

- **低风险**：所有 LLM 实际均走同一模型，合并后行为不变
- **低风险**：删除未使用的 provider 路由逻辑
- **需确认**：`OLLAMA_BASE_URL` 是否被 `embeddings.py` 实际使用，如使用则保留

## 验收标准

- `uv run pytest tests/` 全部通过
- Parser workflow / Analysis / Agent Chat / Parse 所有功能正常
- config.py 模型配置项从 ~15 项降至 2 项
