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

**并发配置（4 项）：**
```
CLASSIFY_MAX_CONCURRENCY
STRUCTURE_MAX_CONCURRENCY
ESCALATE_MAX_CONCURRENCY
TRANSFORM_MAX_CONCURRENCY
```

**不再使用的连接配置（3 项）：**
```
DASHSCOPE_API_KEY
DASHSCOPE_BASE_URL
OLLAMA_BASE_URL
```

### 新增配置（3 项）

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_MODEL` | `MiniMax-2.7` | 所有 LLM 调用统一使用此模型 |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama 部署的嵌入模型 |
| `LLM_MAX_CONCURRENCY` | `10` | 所有 LLM 节点共用并发上限 |

### 保留配置

| 配置 | 保留原因 |
|------|----------|
| `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` | MiniMax 连接凭证 |
| `LLM_API_KEY` / `LLM_BASE_URL` | OpenAI-compatible 备用连接 |
| `OLLAMA_BASE_URL` | 若 embedding 需从配置读取则保留 |

## 代码改动范围

**只改两个地方，不动整体逻辑：**

### 1. `server/config.py`

```python
# 新增
DEFAULT_MODEL: str = "MiniMax-2.7"
EMBEDDING_MODEL: str = "nomic-embed-text"

# 删除（见上方删除列表）
```

### 2. 引用处修改

全量搜索所有 `settings.CLASSIFY_MODEL`、`settings.ESCALATE_MODEL` 等旧配置，将其替换为 `settings.DEFAULT_MODEL`。嵌入模型相关引用替换为 `settings.EMBEDDING_MODEL`。

**不动的地方：**
- `server/llm/` 目录下的 provider 路由逻辑保持不动
- 各 workflow 节点的整体调用逻辑保持不动
- `server/kb/embeddings.py` 不动（`OLLAMA_BASE_URL` 若被使用则保留）

## 实施步骤

1. 修改 `server/config.py`：
   - 新增 `DEFAULT_MODEL`、`EMBEDDING_MODEL`、`LLM_MAX_CONCURRENCY`（3 项）
   - 删除 19 项旧配置（10 模型 + 5 Provider + 4 并发）
2. 全量搜索旧配置引用点并替换：
   - `settings.XXX_MODEL` → `settings.DEFAULT_MODEL`
   - `settings.EMBEDDING_LLM_PROVIDER` → 删除（embedding 独立走 Ollama）
   - `settings.XXX_MAX_CONCURRENCY` → `settings.LLM_MAX_CONCURRENCY`
3. 运行测试验证

## 风险评估

- **低风险**：所有 LLM 实际均走同一模型，替换后行为完全一致
- 不动 `server/llm/` 和 workflow 逻辑，影响范围可控

## 验收标准

- `uv run pytest tests/` 全部通过
- Parser workflow / Analysis / Agent Chat / Parse 所有功能正常
