# Neo4j GB2760 知识图谱集成设计

**日期：** 2026-03-20
**状态：** 已确认（v3 — 修复 7 个审查问题）
**范围：** 仅实现查询层（不含数据导入）

---

## 背景

`server/agent/tools/neo4j_query.py` 目前是占位符，调用后直接返回 "not implemented"。
`pdf_test` 项目已将 GB2760_2024 食品添加剂国标数据完整导入 Neo4j，节点均带有 `embedding` 属性（Ollama `qwen3-embedding:4b`）且已建向量索引。

本次集成目标：补全查询工具，让 Agent 能通过两阶段流程准确回答 GB2760 相关问题：
1. **实体解析** — 用向量语义匹配将用户口语化表达（如"菜罐头"）解析为图谱中的精确节点
2. **结构化查询** — 用精确 code/id 拼 Cypher，执行只读查询取得限量、功能等信息

---

## 前置条件

实施前需确认 Neo4j 中实际存在以下向量索引（执行 `SHOW VECTOR INDEXES`）：
索引名规则为 `{label.lower()}_embedding`，已在 `pdf_test/create_vector_indexes.py` 中验证：

| 索引名 | 对应节点 |
|--------|---------|
| `chemical_embedding` | Chemical |
| `function_embedding` | Function |
| `foodcategory_embedding` | FoodCategory |
| `flavoring_embedding` | Flavoring |
| `processingaid_embedding` | ProcessingAid |
| `enzyme_embedding` | Enzyme |
| `organism_embedding` | Organism |

---

## 架构

### 文件变更（共 6 处）

```
server/
├── agent/
│   ├── tools/
│   │   ├── __init__.py                 ← 新增 neo4j_vector_search 导出
│   │   ├── neo4j_client.py             ← 新建（共享 driver 单例）
│   │   ├── neo4j_query.py              ← 补全实现
│   │   └── neo4j_vector_search.py      ← 新建
│   ├── skills/
│   │   └── neo4j-graph/
│   │       └── SKILL.md               ← 更新
│   └── factory.py                     ← 新增 neo4j_vector_search 注册
└── config.py                          ← 新增 NEO4J_DATABASE 字段
```

另需在 `pyproject.toml` 的 `[tool.pytest.ini_options] markers` 中注册 `integration` marker。

### 两阶段数据流

```
用户问题（如"菜罐头能用哪些防腐剂？"）
  ↓
【阶段一：实体解析】
  Agent 识别实体：食品名="菜罐头"，功能="防腐剂"
  → neo4j_vector_search("菜罐头", "FoodCategory")
    → 返回 [{"code":"06.03.02","name":"蔬菜罐头","score":0.92}, ...]
  → neo4j_vector_search("防腐剂", "Function")
    → 返回 [{"name":"防腐剂","score":0.98}]
  若 top-1 score < 0.7，向用户列出候选项请求确认
  ↓
【阶段二：结构化查询】
  Agent 用确定的 code/name 拼 Cypher：
  → neo4j_query("MATCH (c:Chemical)-[:HAS_FUNCTION]->(:Function {name:'防腐剂'})
                 WITH c MATCH (c)-[r:PERMITTED_IN]->(f:FoodCategory {code:'06.03.02'})
                 RETURN c.name_zh, r.max_usage, r.unit LIMIT 50")
  → 返回 JSON 结果
  ↓
Agent 组织自然语言回答，明确引用限量值和食品分类名称
```

---

## 组件设计

### 1. `neo4j_client.py`（共享 driver 单例）

从 `config.py` 读取 `NEO4J_URI`、`NEO4J_USERNAME`、`NEO4J_PASSWORD`、`NEO4J_DATABASE`，提供懒初始化的模块级 driver 单例。

driver 初始化时设连接级超时（`connection_timeout=30`，单位秒），以兜住网络挂起场景。`GraphDatabase.driver` 本身线程安全，无需加锁；连接失败由调用方错误处理兜底。

暴露两个函数：
- `get_driver() -> neo4j.Driver` — 返回单例 driver（含连接超时配置）
- `get_database() -> str` — 返回数据库名

---

### 2. `neo4j_query.py`（补全实现）

**函数签名：**
```python
@tool
def neo4j_query(query: str) -> str:
    """对 GB2760_2024 知识图谱执行只读 Cypher 查询，返回 JSON 结果"""
```

**约束：**
- 只读事务：`session.execute_read(tx_fn)`，从驱动层强制只读，tx_fn 内调用 `tx.run(query)`
- LIMIT 注入：`re.search(r'\bLIMIT\b', query, re.IGNORECASE)` 检测，无则末尾追加 `LIMIT 50`
- 超时：通过 `neo4j_client.get_driver()`（`connection_timeout=30`）在连接层控制，不使用 `neo4j.Query(timeout)` ——后者与 `execute_read()` 不兼容
- driver 从 `neo4j_client.get_driver()` 获取，替换整个函数含 docstring

**返回格式：**
```json
{"columns": ["name_zh", "max_usage", "unit"], "rows": [["山梨酸", "1.0", "g/kg"]], "count": 1}
```

**错误处理：** 连接失败和语法错误均返回可读字符串（不抛异常）

---

### 3. `neo4j_vector_search.py`（新建）

**函数签名：**
```python
@tool
def neo4j_vector_search(text: str, node_label: str, top_k: int = 5) -> str:
    """
    语义搜索 GB2760_2024 图谱节点，将用户模糊表达解析为精确实体。

    Args:
        text: 搜索文本（如"菜罐头"、"防腐剂"）
        node_label: 节点类型，支持 Chemical/FoodCategory/Function/Flavoring/ProcessingAid/Enzyme/Organism
        top_k: 返回最相似节点数，默认 5
    """
```

**Ollama 调用规格：**
- 端点：`{settings.OLLAMA_BASE_URL}/api/embed`（POST）
- 请求体：`{"model": "qwen3-embedding:4b", "input": text}`
- 响应取值：`response.json()["embeddings"][0]`
- 超时：30 秒（与数据导入时一致）
- HTTP 库：`requests`（已在 pyproject.toml 中）

**向量索引映射：**
```python
INDEX_MAP = {
    "Chemical":      "chemical_embedding",
    "Function":      "function_embedding",
    "FoodCategory":  "foodcategory_embedding",
    "Flavoring":     "flavoring_embedding",
    "ProcessingAid": "processingaid_embedding",
    "Enzyme":        "enzyme_embedding",
    "Organism":      "organism_embedding",
}
```

**向量查询 Cypher（完整语法）：**
```cypher
CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
YIELD node, score
RETURN node, score
```

**各节点类型返回字段：**

| node_label | 返回字段 |
|-----------|---------|
| Chemical | `id`, `name_zh`, `name_en` |
| FoodCategory | `code`, `name` |
| Function | `name` |
| Flavoring | `code`, `name_zh`, `name_en` |
| ProcessingAid | `code`, `name_zh` |
| Enzyme | `code`, `name_zh` |
| Organism | `name_zh`, `name_en` |

**返回格式：**
```json
{
  "node_label": "FoodCategory",
  "results": [{"code": "06.03.02", "name": "蔬菜罐头", "score": 0.92}],
  "count": 1
}
```

**错误处理：**
- 不支持的 `node_label` → 返回支持的类型列表字符串
- Ollama 不可用 → 返回可读错误字符串
- Neo4j 错误 → 返回原始报错字符串

---

### 4. `neo4j-graph/SKILL.md` 更新

**Frontmatter：**
```yaml
---
name: neo4j-graph
description: 用于查询 GB2760_2024 知识图谱中的食品添加剂限量、功能分类、食品分类层级、香料、加工助剂、酶制剂等信息。当用户询问某添加剂在某食品中是否允许使用、最大使用量、具有哪些功能时使用。
allowed-tools: neo4j_query, neo4j_vector_search
---
```

**正文分 5 节（总长 ≤ 200 行）：**
1. 概述：两阶段流程说明
2. 使用步骤：识别实体 → 向量解析（score < 0.7 则询问用户）→ Cypher 查询 → 自然语言回答
3. 可搜索节点类型（6 种 + 标识属性）
4. Schema 速查：节点表 + 关系表（含关系属性：`PERMITTED_IN` 上有 `max_usage`/`unit`/`note`；`PERMITTED_IN_GROUP` 上有 `max_usage`/`exclude_group`）
5. 查询模板（5 个，使用精确 code/name）

---

### 5. 其他文件变更

**`config.py`** 新增：
```python
NEO4J_DATABASE: str = "gb2760_2024"
```

**`factory.py`** 新增导入和工具注册：
```python
from agent.tools import neo4j_vector_search  # 新增
tools = [knowledge_base, get_web_search_tool(), neo4j_query, neo4j_vector_search, postgres_query]
```

**`agent/tools/__init__.py`** 新增导出：
```python
from agent.tools.neo4j_vector_search import neo4j_vector_search
# __all__ 中同步新增 "neo4j_vector_search"
```

**`pyproject.toml`** 注册新 marker：
```toml
markers = [
    "real_llm: tests requiring real LLM/service calls",
    "integration: tests requiring real external services (Neo4j, Ollama)",
]
```

---

## 测试策略

### `tests/core/tools/test_neo4j_query.py`（单元测试，mock driver）

- `test_readonly_transaction`：验证使用 `execute_read`
- `test_limit_injection_when_missing`：无 LIMIT 时末尾追加 `LIMIT 50`
- `test_limit_injection_case_insensitive`：`limit 10` 小写时不覆盖
- `test_connection_error_returns_string`：连接失败返回字符串
- `test_cypher_error_returns_string`：语法错误返回原始报错字符串
- `test_result_json_format`：返回 JSON 含 `columns`、`rows`、`count`

### `tests/core/tools/test_neo4j_vector_search.py`（单元测试，mock requests + driver）

- `test_embedding_request_format`：验证 POST body 含正确 model 和 input 字段
- `test_unsupported_label_returns_error`：不支持的 node_label 返回错误字符串（含支持列表）
- `test_result_json_format`：返回 JSON 含 `node_label`、`results`、`count`
- `test_ollama_error_returns_string`：requests 异常时返回字符串
- `test_top_k_passed_to_query`：验证 top_k 参数传入向量查询

### 集成测试（`@pytest.mark.integration`，默认跳过）

- `test_neo4j_connectivity`：连接 `gb2760_2024` 验证非空
- `test_vector_search_food_category`：搜索"蔬菜罐头"，top-1 应含 code `06.03.02`
- `test_end_to_end_two_phase`：完整两阶段：向量解析 → Cypher 查询

---

## 不在本次范围内

- 数据导入（由 `pdf_test` 手动执行）
- 多数据库支持（gb2760_2014 等）
- Text→Cypher 自动转换
