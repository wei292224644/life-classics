# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指引。

## 项目概览

本仓库为 monorepo，包含：

- `server/` — Python FastAPI 后端：GB 标准 RAG、解析流水线、Chroma + FTS、Agno Agent
- `web/` — **pnpm workspace**（非 Next.js 主应用），当前子应用：
  - `web/apps/console/` — `@acme/console`，React + Vite 管理台（文档上传、Chunk 浏览与编辑、对话等），开发默认端口 **5173**
  - `web/apps/uniapp/` — `@acme/uniapp`，UniApp（H5 / 各小程序），H5 开发端口见 `vite.config.ts`（常与 **5174** 联调）
- `web/ui/` — UI 设计说明与静态 HTML 原型，非独立构建包
- `docker/postgres/` — 可选本地 PostgreSQL（`docker-compose`）

## 执行环境说明

### Git 执行环境

**Git 仓库根目录为项目根目录**，所有 git 命令必须在根目录执行：

```bash
# 正确：在项目根目录执行
git status
git add server/some_file.py
git commit -m "..."

# 错误：不要 cd 进子目录再执行 git
# cd agent-server && git status  ← 禁止
```

### Python 执行环境

`server/` 使用 **uv** 管理 Python 虚拟环境（依赖定义在 `pyproject.toml`）。所有 Python 相关命令在 `server/` 目录下执行，且必须通过 `uv run` 调用：

```bash
cd server
uv run python3 some_script.py

uv run pytest tests/ -v
uv run pytest tests/core/parser_workflow/test_workflow.py -v
```

**安装第三方库必须用 uv，禁止用 pip：**

```bash
cd server
uv add <package>
uv remove <package>
```

### Node 执行环境

`web/` 使用 **pnpm** 管理 Node 依赖。所有 Node 相关命令在 `web/` 目录下执行。

**安装第三方库必须用 pnpm，禁止用 npm 或 yarn：**

```bash
cd web
pnpm add <package>
pnpm add <package> --filter @acme/console
pnpm remove <package>
```

**根目录 `web/package.json` 常用脚本（在 `web/` 下执行）：**

| 脚本 | 说明 |
|------|------|
| `pnpm dev:console` | 启动 console（Vite） |
| `pnpm dev:uniapp:h5` | UniApp H5 |
| `pnpm dev:uniapp:weapp` 等 | 各端小程序开发 |
| `pnpm build:console` / `pnpm build:uniapp:weapp` | 构建 |

仓库根目录 `start.sh` 可用 **tmux** 同时拉起 server（9999）、uniapp H5（5174）、console（5173）。

## server 常用命令

所有命令在 `server/` 目录下执行。

**安装依赖：**

```bash
uv sync
```

**启动服务：**

```bash
uv run python3 run.py
# 或：uv run uvicorn api.main:app --host 0.0.0.0 --port 9999 --reload
```

- 服务：http://localhost:9999  
- Swagger：http://localhost:9999/swagger  
- Prometheus：`GET /metrics`  
- OpenTelemetry：由 `observability/` 配置，默认 OTLP `OTEL_EXPORTER_OTLP_ENDPOINT`

**运行测试：**

```bash
uv run pytest tests/ -v
uv run pytest tests/core/parser_workflow/test_workflow.py -v
```

## 架构说明

### 核心数据结构

`server/parser/models.py` 定义了贯穿处理流水线的核心数据模型：

- `DocumentChunk`（TypedDict）— 最终输出的 chunk，包含 `chunk_id`、`structure_type`、`semantic_type`、`content`、`raw_content`、`section_path`、`doc_metadata`、`meta`
- `TypedSegment` — 分类后的文本段，双维度分类：
  - `structure_type`：`paragraph` / `list` / `table` / `formula` / `header`
  - `semantic_type`：`metadata` / `scope` / `limit` / `procedure` / `material` / `calculation` / `definition` / `amendment`
- `WorkflowState` — LangGraph 状态

### 文档处理流水线（Parser Workflow）

基于 LangGraph 的 9 节点有向图（`server/parser/graph.py`）：

```
Markdown → parse → clean → structure → slice → classify → [escalate] → enrich → transform → merge → DocumentChunk[]
```

各节点职责（`server/parser/nodes/`）：

1. **parse_node** — 解析 Markdown 为原始 chunk（按标题切分）
2. **clean_node** — 清洗内容
3. **structure_node** — LLM 推断结构类型
4. **slice_node** — 按粒度进一步切分
5. **classify_node** — LLM 分类语义类型（规则见 `parser/rules/`）
6. **escalate_node** — 低置信度二次判断
7. **enrich_node** — 交叉引用富化
8. **transform_node** — 内容转换（如表格→自然语言）
9. **merge_node** — 合并相邻同类 chunk

规则配置位于 `server/parser/rules/`。结构化 LLM 输出（Instructor）封装于 `server/parser/structured_llm/`。

### 存储层（`server/kb/`）

- **写入**（`writer/`）：`chroma_writer`、`fts_writer`
- **检索**（`retriever/`）：向量 + BM25 → RRF → 可选 Reranker
- **嵌入**（`embeddings.py`）：嵌入模型封装
- **客户端**（`clients.py`）：ChromaDB 连接管理

### Agent

`server/agent/agent.py` 使用 **Agno** 构建统一 Agent：自定义 `knowledge_base` 工具 + DuckDuckGo + Neo4j + PostgreSQL（及 `neo4j_vector_search` 等，以 `agent/tools/` 为准），Skills 从 `server/agent/skills/` 加载。

HTTP 入口：`POST /api/agent/chat`（`api/agent/router.py`）。

### LLM 与连接

通过 `server/config.py`（Pydantic Settings，读取 `server/.env`）配置：

- **DashScope**：`DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`
- **Ollama**：`OLLAMA_BASE_URL`
- **通用 OpenAI 兼容**：`LLM_BASE_URL`、`LLM_API_KEY`；对话可覆盖为 `CHAT_BASE_URL`、`CHAT_API_KEY`
- Provider 适配见 `server/llm/`

### Parser 与嵌入（择要）

- `PARSER_LLM_PROVIDER`（默认 `openai`，可选 `dashscope` / `ollama`）及节点级 `CLASSIFY_LLM_PROVIDER` 等
- `CLASSIFY_MODEL`、`ESCALATE_MODEL`、`TRANSFORM_MODEL`、`DOC_TYPE_LLM_MODEL`
- `EMBEDDING_MODEL`、`EMBEDDING_LLM_PROVIDER`
- `CHUNK_SOFT_MAX`、`CHUNK_HARD_MAX`、`CONFIDENCE_THRESHOLD`、`RULES_DIR` 等

### 可观测性

- `LOG_LEVEL`、`OTEL_SERVICE_NAME`、`OTEL_EXPORTER_OTLP_ENDPOINT`
- `POST /api/logs` — 前端错误日志上报（`api/frontend_logs/`）

### API 端点

模块化路由（`server/api/`，前缀 `/api`）。完整列表见 **Swagger** 与 [server/README.md](server/README.md)。

**Documents** (`/api/documents`)：

- `GET /api/documents` — 列出文档
- `POST /api/documents` — 上传（SSE，UTF-8 Markdown 等）
- `PATCH /api/documents/{doc_id}` — 更新元数据
- `DELETE /api/documents/clear` — 清空
- `DELETE /api/documents/{doc_id}` — 删除

**Chunks** (`/api/chunks`)：

- `GET /api/chunks` — 分页（`doc_id`、`semantic_type`、`section_path` 等）
- `GET /api/chunks/{chunk_id}` — 单个 chunk
- `PUT /api/chunks/{chunk_id}` — 更新 chunk
- `DELETE /api/chunks/{chunk_id}` — 删除

**Knowledge Base** (`/api/kb`)：

- `GET /api/kb/stats` — 统计
- `DELETE /api/kb` — 清空知识库

**Search & Chat**：

- `POST /api/search` — 混合检索
- `POST /api/chat` — RAG 对话
- `POST /api/chat/stream/start` + `GET /api/chat/stream/{session_id}` — 流式对话（SSE）

**Agent** (`/api/agent`)：

- `POST /api/agent/chat` — Agent 对话

**其他**：

- `POST /api/logs` — 前端日志
- `GET /api/product` — 条形码查询产品（依赖 PostgreSQL 等）

### 关键配置（`server/config.py`）

所有配置项均支持环境变量覆盖。除上文 Parser/LLM 外，常用项包括：

- **存储**：`CHROMA_PERSIST_DIR`（默认 `./db`）、`FTS_DB_PATH`（默认 `./db/knowledge_base_fts.db`）
- **Neo4j**：`NEO4J_URI`、`NEO4J_USERNAME`、`NEO4J_PASSWORD`、`NEO4J_DATABASE`
- **PostgreSQL**：`POSTGRES_HOST`、`POSTGRES_PORT`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`，或 **`POSTGRES_URL`**（优先级更高）
- **对话 Agent**：`CHAT_PROVIDER`、`CHAT_MODEL`、`CHAT_TEMPERATURE`、`AGENT_SKILLS_PATH`、`AGENT_MAX_ITERATIONS`
- **Reranker**：`RERANKER_MODEL`

文档上传路径为 **UTF-8 文本**；若需 PDF，请在仓库外转为 Markdown 再上传（本仓库不设 `MINERU_*` 等内置 PDF 服务配置）。

### 规划文档

`server/docs/plans/` 包含分阶段实现计划（TDD）。实现新功能前请先阅读。

### 测试

测试位于 `server/tests/`：

- `tests/api/` — API 层
- `tests/core/parser_workflow/` — 流水线节点（体量最大）
- `tests/core/kb/` — 检索与写入
- `tests/core/agent/` — Agent
- `tests/assets/` — GB 标准 Markdown 样例
- `tests/artifacts/` — 流水线快照回归

## UI 设计上下文（拍照到分析）
- **一步完成拍照到判断**：拍照与正在分析应尽量合并在同一页面，以分步骤/折叠降低认知切换成本。
- **渐进式分析反馈**：拍完后用阶段提示/进度条/骨架屏让用户知道“正在做”，避免长时间空等。
- **结果第一屏先给结论**：结果需要展示时，首屏优先“一句话结论（能不能吃/是否存在风险）”，细节与原因后置。
- **分析包含第三步“生成评估报告”**：analysis 页 stepper 第 3 步为“生成评估报告”；分析完成后直接跳转 `web/ui/03-result.html`（结果页），不在分析页停留。
