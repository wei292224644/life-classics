# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指引。

## 项目概览

本仓库为 monorepo，包含：
- `agent-server/` — Python FastAPI 后端：基于 RAG 的多工具 Agent，用于查询中国食品安全国家标准（GB 标准）
- `web/apps/console/` — React/Vite 管理界面（知识库 Chunk 浏览与编辑）
- `web/` — Next.js/React 前端（Turbo monorepo）

## 执行环境说明

### Git 执行环境
**Git 仓库根目录为项目根目录（`/life-classics/`）**，所有 git 命令必须在根目录执行：
```bash
# 正确：在项目根目录执行
git status
git add agent-server/some_file.py
git commit -m "..."

# 错误：不要 cd 进子目录再执行 git
# cd agent-server && git status  ← 禁止
```

### Python 执行环境
`agent-server/` 使用 **uv** 管理 Python 虚拟环境（依赖定义在 `pyproject.toml`）。所有 Python 相关命令在 `agent-server/` 目录下执行，且必须通过 `uv run` 调用：

```bash
# 所有 Python 命令格式：uv run python3 ...
cd agent-server
uv run python3 some_script.py

# 测试也通过 uv run 执行
uv run pytest tests/ -v
uv run pytest tests/core/parser_workflow/test_workflow.py -v
```

## agent-server 常用命令

所有命令在 `agent-server/` 目录下执行。

**安装依赖：**
```bash
uv sync
```

**启动服务：**
```bash
uv run python3 run.py
# 或：uv run uvicorn app.main:app --host 0.0.0.0 --port 9999 --reload
```
服务地址：http://localhost:9999 | Swagger 文档：http://localhost:9999/swagger

**运行所有测试：**
```bash
uv run pytest tests/ -v
```

**运行单个测试文件：**
```bash
uv run pytest tests/core/parser_workflow/test_workflow.py -v
```


## 架构说明

### 核心数据结构

`app/core/parser_workflow/models.py` 定义了贯穿处理流水线的核心数据模型：
- `DocumentChunk`（TypedDict）— 最终输出的 chunk，包含 `chunk_id`、`structure_type`、`semantic_type`、`content`、`raw_content`、`section_path`、`doc_metadata`、`meta`
- `TypedSegment` — 分类后的文本段，使用双维度分类体系：
  - `structure_type`：结构维度（`paragraph` / `list` / `table` / `formula` / `header`）
  - `semantic_type`：语义维度（`metadata` / `scope` / `limit` / `procedure` / `material` / `calculation` / `definition` / `amendment`）
- `WorkflowState` — LangGraph 状态，串联整个流水线

### 文档处理流水线（Parser Workflow）

基于 LangGraph 构建的 9 节点有向图（`app/core/parser_workflow/graph.py`）：

```
Markdown → parse → clean → structure → slice → classify → [escalate] → enrich → transform → merge → DocumentChunk[]
```

各节点职责（`app/core/parser_workflow/nodes/`）：
1. **parse_node** — 解析 Markdown 为原始 chunk（按标题切分）
2. **clean_node** — 清洗内容（去噪、格式规范化）
3. **structure_node** — LLM 推断结构类型
4. **slice_node** — 按粒度进一步切分
5. **classify_node** — LLM 分类语义类型（基于 `rules/content_type_rules.json`）
6. **escalate_node** — 处理分类置信度低的 chunk（LLM 二次判断）
7. **enrich_node** — 交叉引用富化（解析表格引用等）
8. **transform_node** — 内容转换（表格→自然语言等）
9. **merge_node** — 合并相邻同类 chunk

规则配置文件位于 `app/core/parser_workflow/rules/`。
结构化 LLM 输出（Instructor）封装于 `app/core/parser_workflow/structured_llm/`。

### 存储层（`app/core/kb/`）

- **写入**（`writer/`）：`chroma_writer` 写入 ChromaDB 向量库，`fts_writer` 写入全文索引
- **检索**（`retriever/`）：`vector_retriever`（向量检索）+ `fts_retriever`（BM25 全文检索）→ `rrf`（RRF 融合排序）→ `rerank`（Qwen3-Reranker 重排序）
- **嵌入**（`embeddings.py`）：嵌入模型封装
- **客户端**（`clients.py`）：ChromaDB 连接管理

### Agent

`app/core/agent/` 提供两种 Agent：

1. **国标 RAG Agent**（`factory.py`）— 基于 Deep Agents + LangGraph 构建，注册 `app/core/tools/` 中的工具：
   - `knowledge_base` — 混合检索（向量 + BM25 + Reranker）
   - `web_search` — DuckDuckGo 搜索
   - `neo4j_query` — 图数据库查询
   - `postgres_query` — SQL 查询

2. **食品安全助手**（`food_safety_agent.py`）— 基于 Agno 框架，通过 `agent_type="food_safety"` 路由

Agent 技能以 Markdown 形式定义在 `app/skills/`。

### LLM 提供商

通过 `app/core/config.py`（Pydantic Settings，读取 `.env`）配置：
- **DashScope**（阿里通义千问）— 主要提供商，设置 `DASHSCOPE_API_KEY`
- **Ollama** — 本地模型，设置 `OLLAMA_BASE_URL`
- **OpenRouter** — 多模型代理

提供商和模型选择可通过环境变量在运行时完全配置。Provider 适配器见 `app/core/llm/`。

### API 端点

5 个模块化路由（`app/api/`）：

**Documents** (`/api/documents`)：
- `GET /api/documents` — 列出所有文档
- `POST /api/documents` — 上传文档
- `DELETE /api/documents/clear` — 清空所有文档
- `DELETE /api/documents/{doc_id}` — 删除指定文档

**Chunks** (`/api/chunks`)：
- `GET /api/chunks` — 分页查询 chunk（支持 `doc_id`、`semantic_type`、`section_path` 过滤）
- `GET /api/chunks/{chunk_id}` — 获取单个 chunk
- `PUT /api/chunks/{chunk_id}` — 更新 chunk
- `DELETE /api/chunks/{chunk_id}` — 删除 chunk

**Knowledge Base** (`/api/kb`)：
- `GET /api/kb/stats` — 知识库统计信息
- `DELETE /api/kb` — 清空知识库

**Search & Chat** (`/api`)：
- `POST /api/search` — 混合检索
- `POST /api/chat` — RAG 对话
- `POST /api/chat/stream/start` + `GET /api/chat/stream/{session_id}` — 流式对话（SSE）

**Agent** (`/api/agent`)：
- `POST /api/agent/chat` — 多工具 Agent 对话（支持 `agent_type` 路由）

### 关键配置（`app/core/config.py`）

所有配置项均支持环境变量覆盖。关键变量：
- `LLM_PROVIDER`、`CHAT_MODEL`、`EMBEDDING_MODEL`
- `DASHSCOPE_API_KEY`、`OLLAMA_BASE_URL`
- `NEO4J_URI`、`NEO4J_USERNAME`、`NEO4J_PASSWORD`
- `POSTGRES_URL`
- `MINERU_SERVICE_URL` — 外部 PDF→Markdown 转换服务
- `CHROMA_PERSIST_DIR`（默认：`chroma_db/`）

### 规划文档

`agent-server/docs/plans/` 包含详细的分阶段实现计划（基于 TDD）。实现新功能前请先阅读——系统针对 GB 标准制定了特定的切分和分类规则。

### 测试

测试位于 `agent-server/tests/`，按模块组织：
- `tests/api/` — API 层服务测试（documents / chunks / kb）
- `tests/core/parser_workflow/` — 流水线节点测试（最大的测试目录）
- `tests/core/kb/` — 检索与写入测试
- `tests/core/agent/` — Agent 测试
- `tests/assets/` — GB 标准 Markdown 测试文件
- `tests/artifacts/` — 流水线运行快照（用于回归测试）
