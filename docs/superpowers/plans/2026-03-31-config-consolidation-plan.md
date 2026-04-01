# Config 合并实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan.

**Goal:** 将 `server/config.py` 中 20+ 项配置简化为 5 项（DEFAULT_MODEL / EMBEDDING_MODEL / LLM_MAX_CONCURRENCY + 保留项），并更新所有引用处。

**Architecture:** 所有 LLM 调用统一走 MiniMax-2.7，embedding 走 Ollama，并发上限统一为一个值。

**Tech Stack:** Pydantic Settings, asyncio.Semaphore

---

## 改动范围总览

| 类型 | 数量 | 操作 |
|------|------|------|
| 模型配置 | 11 项 | 删除 → 合并为 DEFAULT_MODEL |
| Provider 配置 | 5 项 | 删除 |
| 并发配置 | 4 项 | 删除 → 合并为 LLM_MAX_CONCURRENCY |
| 新增配置 | 3 项 | DEFAULT_MODEL / EMBEDDING_MODEL / LLM_MAX_CONCURRENCY |

**删除项总计：20 项**

---

## 需修改的文件

| 文件 | 改动 |
|------|------|
| `server/config.py` | 删除 20 项，新增 3 项 |
| `server/workflow_product_analysis/product_agent/nodes.py` | provider/model 引用 → DEFAULT_MODEL |
| `server/workflow_product_analysis/ingredient_parser.py` | provider/model 引用 → DEFAULT_MODEL |
| `server/workflow_product_analysis/pipeline.py` | INGREDIENT_ANALYSIS_MODEL → DEFAULT_MODEL |
| `server/agent/agent.py` | CHAT_MODEL → DEFAULT_MODEL |
| `server/api/search/service.py` | CHAT_PROVIDER/CHAT_MODEL → 删除 provider，model → DEFAULT_MODEL |
| `server/kb/embeddings.py` | EMBEDDING_LLM_PROVIDER fallback 逻辑删除 |
| `server/workflow_parser_kb/structured_gateway.py` | provider 解析 → 直接硬编码 "anthropic" |
| `server/workflow_parser_kb/nodes/classify_node.py` | CLASSIFY_MODEL / CLASSIFY_MAX_CONCURRENCY |
| `server/workflow_parser_kb/nodes/structure_node.py` | DOC_TYPE_LLM_MODEL / STRUCTURE_MAX_CONCURRENCY |
| `server/workflow_parser_kb/nodes/escalate_node.py` | ESCALATE_MODEL / ESCALATE_MAX_CONCURRENCY |
| `server/workflow_parser_kb/nodes/transform_node.py` | TRANSFORM_MODEL / TRANSFORM_MAX_CONCURRENCY |
| `server/tests/core/kb/test_embeddings.py` | mock EMBEDDING_LLM_PROVIDER / PARSER_LLM_PROVIDER 相关测试用例调整 |
| `server/tests/core/parser_workflow/test_llm.py` | 清理已注释掉的 PARSER_LLM_PROVIDER 用例 |

---

## Task 1: 修改 `server/config.py`

**文件:** `server/config.py`

- [ ] **Step 1: 新增 3 项配置**

在 `# ── 各用途模型 ──────────────────────────────────────────────────────────` 小节下方添加：

```python
# ── 统一模型配置 ────────────────────────────────────────────────────────────
DEFAULT_MODEL: str = "MiniMax-2.7"          # 所有 LLM 调用统一使用此模型
EMBEDDING_MODEL: str = "nomic-embed-text"   # Ollama 部署的嵌入模型
LLM_MAX_CONCURRENCY: int = 10               # 所有 LLM 节点共用并发上限
```

- [ ] **Step 2: 删除旧模型配置项（10 项）**

删除以下配置行：
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

- [ ] **Step 3: 删除旧 Provider 配置项（5 项）**

删除以下配置行：
```
PARSER_LLM_PROVIDER
CLASSIFY_LLM_PROVIDER
ESCALATE_LLM_PROVIDER
TRANSFORM_LLM_PROVIDER
DOC_TYPE_LLM_PROVIDER
PARSE_LLM_PROVIDER
CHAT_PROVIDER
EMBEDDING_LLM_PROVIDER
```

- [ ] **Step 4: 删除旧并发配置项（4 项）**

删除以下配置行：
```
CLASSIFY_MAX_CONCURRENCY
STRUCTURE_MAX_CONCURRENCY
ESCALATE_MAX_CONCURRENCY
TRANSFORM_MAX_CONCURRENCY
```

- [ ] **Step 5: 提交**

```bash
git add server/config.py
git commit -m "refactor(config): 合并 20+ 项模型/provider/并发配置为 3 项"
```

---

## Task 2: 更新 Parser workflow 节点引用

**文件:**
- `server/workflow_parser_kb/nodes/classify_node.py:169,222,251`
- `server/workflow_parser_kb/nodes/structure_node.py:91,116`
- `server/workflow_parser_kb/nodes/escalate_node.py:98,114,140`
- `server/workflow_parser_kb/nodes/transform_node.py:33,148`

- [ ] **Step 1: 更新 classify_node.py**

```python
# 第 169 行
llm_calls_total.labels(node="classify_node", model=settings.DEFAULT_MODEL).inc()

# 第 222 行
semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENCY)

# 第 251 行
model=settings.DEFAULT_MODEL,
```

- [ ] **Step 2: 更新 structure_node.py**

```python
# 第 91 行
node="structure_node", model=settings.DEFAULT_MODEL or "unknown"

# 第 116 行
semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENCY)
```

- [ ] **Step 3: 更新 escalate_node.py**

```python
# 第 98 行
semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENCY)

# 第 114 行
llm_calls_total.labels(node="escalate_node", model=settings.DEFAULT_MODEL).inc()

# 第 140 行
model=settings.DEFAULT_MODEL,
```

- [ ] **Step 4: 更新 transform_node.py**

```python
# 第 33 行（删除 or fallback 逻辑，直接用 DEFAULT_MODEL）
return settings.DEFAULT_MODEL

# 第 148 行
semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENCY)
```

- [ ] **Step 5: 提交**

```bash
git add server/workflow_parser_kb/nodes/classify_node.py \
  server/workflow_parser_kb/nodes/structure_node.py \
  server/workflow_parser_kb/nodes/escalate_node.py \
  server/workflow_parser_kb/nodes/transform_node.py
git commit -m "refactor(parser): 统一 model 和 concurrency 配置引用"
```

---

## Task 3: 更新 structured_gateway.py

**文件:** `server/workflow_parser_kb/structured_gateway.py:58`

- [ ] **Step 1: 简化 provider 解析**

第 58 行当前：
```python
provider = resolve_provider_for_node(node_provider or None, settings.PARSER_LLM_PROVIDER or None)
```

修改为（直接硬编码 anthropic，因为所有 LLM 均走 MiniMax）：
```python
provider = "anthropic"
```

- [ ] **Step 2: 提交**

```bash
git add server/workflow_parser_kb/structured_gateway.py
git commit -m "refactor(structured_gateway): 硬编码 provider 为 anthropic"
```

---

## Task 4: 更新 product_analysis 引用

**文件:**
- `server/workflow_product_analysis/product_agent/nodes.py:34-35,52,70-71,83,101-102,125,141-142,162`
- `server/workflow_product_analysis/ingredient_parser.py:48-49`
- `server/workflow_product_analysis/pipeline.py:194`

- [ ] **Step 1: 更新 product_agent/nodes.py**

将所有节点中的 `provider=settings.ANALYSIS_LLM_PROVIDER` 和 `model=settings.ANALYSIS_XXX_MODEL` 替换为：
```python
provider="anthropic",
model=settings.DEFAULT_MODEL,
```

共涉及 4 个节点（demographics / scenarios / advice / verdict），每处两行。

- [ ] **Step 2: 更新 ingredient_parser.py:48-49**

```python
# 当前：
provider = settings.PARSE_LLM_PROVIDER
model = settings.PARSE_MODEL

# 改为：
provider = "anthropic"
model = settings.DEFAULT_MODEL
```

- [ ] **Step 3: 更新 pipeline.py:194**

```python
# 当前：
"ai_model": settings.INGREDIENT_ANALYSIS_MODEL,

# 改为：
"ai_model": settings.DEFAULT_MODEL,
```

- [ ] **Step 4: 提交**

```bash
git add server/workflow_product_analysis/product_agent/nodes.py \
  server/workflow_product_analysis/ingredient_parser.py \
  server/workflow_product_analysis/pipeline.py
git commit -m "refactor(product_analysis): 统一 model 引用为 DEFAULT_MODEL"
```

---

## Task 5: 更新 Agent 和 Search 引用

**文件:**
- `server/agent/agent.py:40`
- `server/api/search/service.py:122-123,165-166`

- [ ] **Step 1: 更新 agent.py:40**

```python
# 当前：
id=settings.CHAT_MODEL,

# 改为：
id=settings.DEFAULT_MODEL,
```

- [ ] **Step 2: 更新 search/service.py**

第 122-123 行和 165-166 行，将：
```python
provider_name=settings.CHAT_PROVIDER,
model=settings.CHAT_MODEL,
```

改为：
```python
provider_name="anthropic",
model=settings.DEFAULT_MODEL,
```

- [ ] **Step 3: 提交**

```bash
git add server/agent/agent.py server/api/search/service.py
git commit -m "refactor(agent/search): 统一 model 引用为 DEFAULT_MODEL"
```

---

## Task 6: 更新 embeddings.py

**文件:** `server/kb/embeddings.py:12`

- [ ] **Step 1: 简化 provider fallback**

当前：
```python
provider = settings.EMBEDDING_LLM_PROVIDER or settings.PARSER_LLM_PROVIDER
```

改为（embedding 独立走 Ollama，无需 fallback）：
```python
provider = "ollama"
```

> **注意：** `OLLAMA_BASE_URL` 保留（`embeddings.py` 需要用）。

- [ ] **Step 2: 提交**

```bash
git add server/kb/embeddings.py
git commit -m "refactor(embeddings): 硬编码 provider 为 ollama"
```

---

## Task 7: 更新测试文件

**文件:**
- `server/tests/core/kb/test_embeddings.py`
- `server/tests/core/parser_workflow/test_llm.py`

- [ ] **Step 1: 更新 test_embeddings.py**

删除以下 mock 相关行：
- 第 23-24 行：`mock_settings.EMBEDDING_LLM_PROVIDER` 和 `mock_settings.PARSER_LLM_PROVIDER`
- 第 44-45 行：同上
- 第 65-66 行：同上

由于 `EMBEDDING_LLM_PROVIDER` 已删除，相关测试用例的 mock 需删除，只保留 `provider = "ollama"` 的行为验证。

- [ ] **Step 2: 清理 test_llm.py 中的注释代码**

删除或取消注释第 17-28 行已注释掉的 `PARSER_LLM_PROVIDER` 相关代码（清理死注释）。

- [ ] **Step 3: 提交**

```bash
git add server/tests/core/kb/test_embeddings.py \
  server/tests/core/parser_workflow/test_llm.py
git commit -m "test: 清理已删除配置的 mock 和注释"
```

---

## Task 8: 验收测试

- [ ] **Step 1: 运行全量测试**

```bash
cd server && uv run pytest tests/ -v --tb=short
```

- [ ] **Step 2: 确认结果**

预期：
- 所有测试通过（或仅有与本次改动无关的失败）
- 无 `AttributeError: setting 'XXX_MODEL' not found` 错误

---

## 自检清单

- [ ] config.py 新增 3 项，删除 20 项
- [ ] 所有 `settings.XXX_MODEL` 引用已替换为 `settings.DEFAULT_MODEL`
- [ ] 所有 `settings.XXX_MAX_CONCURRENCY` 引用已替换为 `settings.LLM_MAX_CONCURRENCY`
- [ ] `settings.EMBEDDING_LLM_PROVIDER` 和 `settings.PARSER_LLM_PROVIDER` 不再被引用
- [ ] `settings.ANALYSIS_LLM_PROVIDER` / `settings.PARSE_LLM_PROVIDER` / `settings.CHAT_PROVIDER` 不再被引用
- [ ] `server/llm/` 目录未做修改（逻辑不动）
- [ ] 测试通过
