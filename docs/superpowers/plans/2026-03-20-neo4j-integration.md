# Neo4j GB2760 知识图谱集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全 `neo4j_query` 工具并新增 `neo4j_vector_search` 工具，让 Agent 通过两阶段流程（向量实体解析 → Cypher 结构化查询）准确回答 GB2760_2024 食品添加剂相关问题。

**Architecture:** 新建共享 driver 单例模块 `neo4j_client.py`；`neo4j_query` 为纯 async 函数（Agno 风格），使用 `execute_read()` 执行只读 Cypher 并自动注入 LIMIT；`neo4j_vector_search` 调用 Ollama embed API 生成向量后执行向量索引查询；Agno 内置 `Neo4jTools` 禁用 `run_cypher_query`，保留探索性工具；skill 文件指导 Agent 先解析实体再查关系。

**Tech Stack:** Python 3.12, neo4j>=5.0（已有）, requests（已有）, Agno async 函数工具风格, pytest + unittest.mock

> **注意：** `neo4j>=5.0.0` 和 `requests>=2.31.0` 已在 `server/pyproject.toml` 中，无需新增依赖，也不需要执行 `uv add`。工具定义风格为**纯 async 函数**（参考 `server/agent/tools/knowledge_base.py`），**不使用** `@tool` 装饰器。

---

## 文件变更一览

| 操作 | 文件 |
|------|------|
| 修改 | `server/config.py` |
| 修改 | `server/pyproject.toml` |
| 新建 | `server/agent/tools/neo4j_client.py` |
| 新建 | `server/agent/tools/neo4j_query.py` |
| 新建 | `server/agent/tools/neo4j_vector_search.py` |
| 修改 | `server/agent/tools/__init__.py` |
| 修改 | `server/agent/agent.py` |
| 修改 | `server/agent/skills/neo4j-graph/SKILL.md` |
| 新建 | `server/tests/core/tools/test_neo4j_client.py` |
| 新建 | `server/tests/core/tools/test_neo4j_query.py` |
| 新建 | `server/tests/core/tools/test_neo4j_vector_search.py` |
| 新建 | `server/tests/core/tools/test_neo4j_integration.py` |

---

## Task 1：基础配置

**目的：** 在 `config.py` 新增 `NEO4J_DATABASE` 字段，在 `pyproject.toml` 注册 `integration` pytest marker。

**Files:**
- Modify: `server/config.py`
- Modify: `server/pyproject.toml`

- [ ] **Step 1：在 `server/config.py` 的 Neo4j 配置块（`NEO4J_PASSWORD` 之后）新增字段**

```python
NEO4J_DATABASE: str = "gb2760_2024"
```

- [ ] **Step 2：在 `server/pyproject.toml` 的 `[tool.pytest.ini_options] markers` 列表中追加**

```toml
"integration: tests requiring real external services (Neo4j, Ollama)",
```

- [ ] **Step 3：提交（在项目根目录执行）**

```bash
git add server/config.py server/pyproject.toml
git commit -m "feat(neo4j): add NEO4J_DATABASE config and integration pytest marker"
```

---

## Task 2：共享 driver 单例（`neo4j_client.py`）

**目的：** 提供模块级懒初始化 Neo4j driver 单例，供 `neo4j_query` 和 `neo4j_vector_search` 共用，避免重复建连。

**Files:**
- Create: `server/agent/tools/neo4j_client.py`
- Create: `server/tests/core/tools/test_neo4j_client.py`

- [ ] **Step 1：编写测试**

新建 `server/tests/core/tools/test_neo4j_client.py`，包含：

```
test_get_driver_returns_singleton
  目的：两次调用 get_driver() 返回同一对象
  做法：patch GraphDatabase.driver，assert 两次返回结果 is 同一实例，driver 构造函数只被调用一次

test_get_database_returns_configured_value
  目的：get_database() 返回 settings.NEO4J_DATABASE
  做法：直接调用断言返回值为 "gb2760_2024"（或 settings 中的值）
```

- [ ] **Step 2：运行测试，确认失败**

```bash
cd server && uv run pytest tests/core/tools/test_neo4j_client.py -v
```
预期：ImportError（模块不存在）

- [ ] **Step 3：实现 `neo4j_client.py`**

```
文件：server/agent/tools/neo4j_client.py

get_driver() -> neo4j.Driver
  目的：返回全局共享的 Neo4j driver 单例
  参数：无
  返回：neo4j.Driver 实例
  实现：
    - 模块级变量 _driver 初始为 None
    - 首次调用时用 settings.NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD 创建 driver
    - 传入 connection_timeout=30 防止网络挂起
    - 后续调用直接返回已有实例

get_database() -> str
  目的：返回目标 database 名称
  参数：无
  返回：settings.NEO4J_DATABASE 的值
```

- [ ] **Step 4：运行测试，确认通过**

```bash
cd server && uv run pytest tests/core/tools/test_neo4j_client.py -v
```
预期：全部 PASS

- [ ] **Step 5：提交**

```bash
git add server/agent/tools/neo4j_client.py server/tests/core/tools/test_neo4j_client.py
git commit -m "feat(neo4j): add shared neo4j driver singleton module"
```

---

## Task 3：实现 `neo4j_query` 工具

**目的：** 新建纯 async 函数（Agno 风格），接收 Cypher 字符串，在只读事务中执行，自动注入 LIMIT，返回 JSON 字符串。不使用 `@tool` 装饰器，风格与 `knowledge_base.py` 一致。

**Files:**
- Create: `server/agent/tools/neo4j_query.py`
- Create: `server/tests/core/tools/test_neo4j_query.py`

- [ ] **Step 1：编写测试**

新建 `server/tests/core/tools/test_neo4j_query.py`，包含：

```
test_readonly_transaction
  目的：确保调用 execute_read 而非 execute_write
  做法：mock session 上的 execute_read 和 execute_write
        调用工具后 assert execute_read 被调用一次（主断言）
        assert execute_write 未被调用（辅助断言）

test_limit_injection_when_missing
  目的：Cypher 无 LIMIT 时末尾自动追加 LIMIT 50
  做法：mock execute_read，捕获传入 tx.run 的 query 字符串，assert 以 "LIMIT 50" 结尾

test_limit_injection_case_insensitive
  目的：Cypher 含小写 "limit 10" 时不重复追加
  做法：同上，assert query 中只有一个 LIMIT 相关子句

test_connection_error_returns_string
  目的：driver 抛 ServiceUnavailable 时返回字符串而非异常
  做法：mock get_driver() 抛出 neo4j.exceptions.ServiceUnavailable，assert 返回值为 str

test_cypher_error_returns_string
  目的：Cypher 语法错误时返回原始报错字符串
  做法：mock execute_read 内部抛 neo4j.exceptions.CypherSyntaxError，assert 返回值含错误信息

test_result_json_format
  目的：正常查询返回含 columns/rows/count 三个字段的 JSON 字符串
  做法：mock execute_read 返回 [{"name_zh": "山梨酸", "max_usage": "1.0"}]
        assert json.loads 结果有 columns/rows/count 字段
```

- [ ] **Step 2：运行测试，确认失败**

```bash
cd server && uv run pytest tests/core/tools/test_neo4j_query.py -v
```
预期：全部 FAIL（文件不存在）

- [ ] **Step 3：实现 `neo4j_query.py`**

```
文件：server/agent/tools/neo4j_query.py
风格：纯 async 函数，无装饰器，参考 knowledge_base.py

async def neo4j_query(query: str) -> str
  目的：对 GB2760_2024 知识图谱执行只读 Cypher 查询，返回 JSON 字符串
  参数：
    query: Cypher 查询语句
  返回：
    成功：JSON 字符串 {"columns": [...], "rows": [[...], ...], "count": N}
    失败：可读错误字符串（不抛异常，让 Agent 能理解并自行修正）
  实现步骤：
    1. re.search(r'\bLIMIT\b', query, re.IGNORECASE) 检测，无则末尾追加 " LIMIT 50"
    2. 从 neo4j_client.get_driver() 获取 driver
    3. driver.session(database=neo4j_client.get_database()) 开启会话
    4. session.execute_read(lambda tx: list(tx.run(query)))
    5. 将结果转为 {"columns": keys, "rows": values_list, "count": len} JSON 字符串
    6. 捕获所有异常，返回 f"Neo4j 查询失败：{e}" 字符串
```

- [ ] **Step 4：运行测试，确认通过**

```bash
cd server && uv run pytest tests/core/tools/test_neo4j_query.py -v
```
预期：全部 PASS

- [ ] **Step 5：提交**

```bash
git add server/agent/tools/neo4j_query.py server/tests/core/tools/test_neo4j_query.py
git commit -m "feat(neo4j): implement neo4j_query async tool with readonly transaction"
```

---

## Task 4：新建 `neo4j_vector_search` 工具

**目的：** 纯 async 函数，接收文本和节点类型，调用 Ollama 生成 embedding，在 Neo4j 向量索引中查找最相似节点，用于第一阶段实体解析。

**Files:**
- Create: `server/agent/tools/neo4j_vector_search.py`
- Create: `server/tests/core/tools/test_neo4j_vector_search.py`

- [ ] **Step 1：编写测试**

新建 `server/tests/core/tools/test_neo4j_vector_search.py`，包含：

```
test_embedding_request_format
  目的：验证向 Ollama 发送的 POST 请求 URL 和 body 均正确
  做法：mock requests.post，调用工具后：
        assert 请求 URL 包含 "/api/embed"
        assert body 含 {"model": "qwen3-embedding:4b", "input": <text>}

test_unsupported_label_returns_error
  目的：传入不支持的 node_label 时返回错误字符串（含支持列表）
  做法：调用工具传 "InvalidLabel"，assert 返回值为 str 且含支持类型信息

test_result_json_format
  目的：正常调用返回含 node_label/results/count 的 JSON 字符串
  做法：mock requests.post 返回含 embeddings 的响应，mock execute_read 返回节点列表
        assert json.loads 结果含正确字段

test_ollama_error_returns_string
  目的：requests.post 抛异常时返回字符串
  做法：mock requests.post 抛 requests.exceptions.ConnectionError，assert 返回值为 str

test_top_k_passed_to_query
  目的：top_k 参数正确传入向量查询
  做法：mock execute_read，捕获执行的 Cypher 或参数，assert 含正确 top_k 数值
```

- [ ] **Step 2：运行测试，确认失败**

```bash
cd server && uv run pytest tests/core/tools/test_neo4j_vector_search.py -v
```
预期：全部 FAIL（文件不存在）

- [ ] **Step 3：实现 `neo4j_vector_search.py`**

```
文件：server/agent/tools/neo4j_vector_search.py
风格：纯 async 函数，无装饰器

常量：
  INDEX_MAP: dict[str, str]
    Chemical      → "chemical_embedding"
    Function      → "function_embedding"
    FoodCategory  → "foodcategory_embedding"
    Flavoring     → "flavoring_embedding"
    ProcessingAid → "processingaid_embedding"
    Enzyme        → "enzyme_embedding"
    Organism      → "organism_embedding"

  RETURN_FIELDS: dict[str, list[str]]
    Chemical:      ["id", "name_zh", "name_en"]
    FoodCategory:  ["code", "name"]
    Function:      ["name"]
    Flavoring:     ["code", "name_zh", "name_en"]
    ProcessingAid: ["code", "name_zh"]
    Enzyme:        ["code", "name_zh"]
    Organism:      ["name_zh", "name_en"]

_get_embedding(text: str) -> list[float]
  目的：调用 Ollama /api/embed 将文本转为向量
  参数：text — 要嵌入的文本
  返回：float 列表
  异常：失败时抛出 RuntimeError（由调用方捕获）
  实现：
    POST {settings.OLLAMA_BASE_URL}/api/embed
    body: {"model": "qwen3-embedding:4b", "input": text}
    timeout: 30s
    取 response.json()["embeddings"][0]

async def neo4j_vector_search(text: str, node_label: str, top_k: int = 5) -> str
  目的：语义搜索 GB2760_2024 图谱节点，将模糊表达解析为精确实体
  参数：
    text       — 搜索文本（如"菜罐头"）
    node_label — 节点类型（INDEX_MAP 中的 7 种之一）
    top_k      — 返回节点数，默认 5
  返回：
    成功：JSON 字符串 {"node_label": ..., "results": [{...,"score":0.92},...], "count": N}
    失败：可读错误字符串
  实现步骤：
    1. 检查 node_label 是否在 INDEX_MAP，否则返回支持类型列表的错误字符串
    2. 调用 _get_embedding(text)；捕获异常返回错误字符串
    3. 用 neo4j_client.get_driver() 开启只读 session
    4. 执行:
       CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
       YIELD node, score
       RETURN node, score
    5. 按 RETURN_FIELDS[node_label] 提取属性，附上 score，拼入 results 列表
    6. 返回 JSON 字符串；任何异常返回错误字符串
```

- [ ] **Step 4：运行测试，确认通过**

```bash
cd server && uv run pytest tests/core/tools/test_neo4j_vector_search.py -v
```
预期：全部 PASS

- [ ] **Step 5：提交**

```bash
git add server/agent/tools/neo4j_vector_search.py server/tests/core/tools/test_neo4j_vector_search.py
git commit -m "feat(neo4j): implement neo4j_vector_search async tool for entity resolution"
```

---

## Task 5：更新 `__init__.py` 和 `agent.py`

**目的：** 导出新工具，更新 `agent.py`：禁用 `Neo4jTools` 的 `run_cypher_query`（改用自定义工具），注册 `neo4j_query` 和 `neo4j_vector_search`，传入 `database` 参数。

**Files:**
- Modify: `server/agent/tools/__init__.py`
- Modify: `server/agent/agent.py`

- [ ] **Step 1：更新 `server/agent/tools/__init__.py`**

新增导入和导出：
```
新增：from agent.tools.neo4j_query import neo4j_query
新增：from agent.tools.neo4j_vector_search import neo4j_vector_search
__all__ 中同步新增两个名称
```

- [ ] **Step 2：更新 `server/agent/agent.py`**

修改 `create_agent()` 函数中的工具注册部分：

```
1. 在 tools 列表中加入 neo4j_query 和 neo4j_vector_search（从 agent.tools 导入）

2. 修改 Neo4jTools 初始化：
   - 新增 database=settings.NEO4J_DATABASE
   - 新增 enable_run_cypher=False（禁用内置 run_cypher，改用自定义工具）

3. neo4j_query 和 neo4j_vector_search 的注册条件与 Neo4jTools 一致
   （settings.NEO4J_PASSWORD 不为空时才注册）
```

- [ ] **Step 3：运行全量工具测试确认无回归**

```bash
cd server && uv run pytest tests/core/tools/ -v
```
预期：全部 PASS。若出现 ImportError，检查 `__init__.py` 导入路径后重新运行。

- [ ] **Step 4：提交**

```bash
git add server/agent/tools/__init__.py server/agent/agent.py
git commit -m "feat(neo4j): register neo4j_query and neo4j_vector_search, configure Neo4jTools database"
```

---

## Task 6：更新 `neo4j-graph/SKILL.md`

**目的：** 将 skill 文件更新为完整的两阶段查询指引，`allowed-tools` 使用实际暴露的工具函数名。

**Files:**
- Modify: `server/agent/skills/neo4j-graph/SKILL.md`

- [ ] **Step 1：重写 SKILL.md**

完整替换文件内容（总长 ≤ 200 行）：

```
frontmatter:
  name: neo4j-graph
  description: 用于查询 GB2760_2024 知识图谱中的食品添加剂限量、功能分类、食品分类层级、香料、加工助剂、酶制剂等信息。当用户询问某添加剂在某食品中是否允许使用、最大使用量、具有哪些功能时使用。
  allowed-tools: neo4j_query, neo4j_vector_search

节 1：概述
  两阶段流程：neo4j_vector_search 负责实体解析（模糊 → 精确），neo4j_query 负责结构化查询

节 2：使用步骤（两阶段）
  1. 识别问题中的实体（食品名、添加剂名、功能名等）
  2. 对每个不确定的实体调用 neo4j_vector_search(text, node_label)
     若 top-1 score < 0.7，向用户展示候选列表并请求确认
  3. 用确认的 code/name 构建精确 Cypher，调用 neo4j_query 执行
  4. 回答时明确引用限量值（含单位）和食品分类名称

节 3：可向量搜索的节点类型（7 种）
  列出 Chemical/FoodCategory/Function/Flavoring/ProcessingAid/Enzyme/Organism
  及 node_label 传参值和关键标识属性

节 4：Schema 速查
  节点速查表（10 种，紧凑格式）
  关系速查表（8 种，含属性）：
    PERMITTED_IN: max_usage, unit, note
    PERMITTED_IN_GROUP: max_usage, exclude_group
    其余关系无额外属性

节 5：查询模板（5 个，含示例 Cypher）
  1. 查添加剂在特定食品分类的限量
  2. 查添加剂的所有功能
  3. 查食品分类下允许的所有添加剂（带限量）
  4. 查香料是否允许用于某食品
  5. 查食品分类的直接子分类
```

- [ ] **Step 2：确认 frontmatter 格式正确**

```bash
head -6 server/agent/skills/neo4j-graph/SKILL.md
```
预期：`---` / `name:` / `description:` / `allowed-tools:` 均存在

- [ ] **Step 3：提交**

```bash
git add server/agent/skills/neo4j-graph/SKILL.md
git commit -m "feat(neo4j): update neo4j-graph skill with two-phase query workflow"
```

---

## Task 7：集成测试（可选，需真实 Neo4j + Ollama）

**目的：** 验证端到端两阶段流程，确认向量索引名、Ollama 可达性和完整查询链路均正常。

**Files:**
- Create: `server/tests/core/tools/test_neo4j_integration.py`

- [ ] **Step 1：编写集成测试**

```
文件：server/tests/core/tools/test_neo4j_integration.py
所有测试标记 @pytest.mark.integration

test_neo4j_connectivity
  目的：确认 gb2760_2024 database 可连接且含数据
  做法：await neo4j_query("MATCH (n) RETURN count(n) AS cnt")
        assert json.loads(result)["rows"][0][0] > 0

test_vector_search_food_category
  目的：搜索"蔬菜罐头"，top-1 score 应 > 0.7
  做法：await neo4j_vector_search("蔬菜罐头", "FoodCategory")
        assert json.loads(result)["results"][0]["score"] > 0.7

test_end_to_end_two_phase
  目的：完整两阶段：向量解析食品分类 → Cypher 查该分类下的添加剂
  做法：
    1. await neo4j_vector_search("蔬菜罐头", "FoodCategory") 获取 code
    2. await neo4j_query(f"MATCH (c:Chemical)-[r:PERMITTED_IN]->(f:FoodCategory {{code:'{code}'}}) RETURN c.name_zh, r.max_usage, r.unit")
    3. assert 结果含 name_zh 字段
```

- [ ] **Step 2：提交**

```bash
git add server/tests/core/tools/test_neo4j_integration.py
git commit -m "test(neo4j): add integration tests for two-phase query flow"
```

- [ ] **Step 3（可选）：运行集成测试**

```bash
cd server && uv run pytest tests/core/tools/test_neo4j_integration.py -v -m integration
```
预期：需 Neo4j 和 Ollama 均在线，全部 PASS
