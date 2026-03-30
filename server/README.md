# life-classics 服务端

基于 **FastAPI** 的食品安全国标（GB）知识库与 RAG 后端：文档解析流水线（LangGraph）、向量 + 全文检索、多工具 Agent、可选 Neo4j / PostgreSQL 集成。

## 技术栈

- **Web**：FastAPI、SSE 流式响应  
- **解析**：LangGraph 流水线、`server/parser/rules/` 规则与 Anthropic Streaming Tool Use 结构化输出  
- **知识库**：ChromaDB（向量）+ SQLite FTS（BM25）+ Reranker  
- **依赖管理**：**uv**（`pyproject.toml`，勿用 pip 直接装依赖）

## 快速开始

### 环境要求

- Python ≥ 3.10（以 `pyproject.toml` 为准）
- [uv](https://github.com/astral-sh/uv)

### 安装与启动

```bash
cd server
uv sync
# 可选：复制并编辑 .env（见下文「环境变量」）
uv run python3 run.py
```

等价方式：

```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port 9999 --reload
```

- **Swagger**：http://localhost:9999/swagger  
- **Prometheus 指标**：http://localhost:9999/metrics  
- **构建后的管理台**：若存在 `web/apps/console/dist`，可通过 http://localhost:9999/admin 访问（由 `api/main.py` 挂载）

### 测试

```bash
cd server
uv run pytest tests/ -v
uv run pytest tests/core/parser_workflow/test_workflow.py -v
```

---

## 架构分层

| 层级 | 路径 | 说明 |
|------|------|------|
| API | `api/` | REST：`/api/*`；健康与前端日志等 |
| 解析流水线 | `parser/` | LangGraph 图定义、`nodes/`、`rules/`、`structured_llm/` |
| 知识库 | `kb/` | `writer/`（Chroma + FTS）、`retriever/`、嵌入与客户端 |
| Agent | `agent/` | 对话与工具、`agent/skills/` |
| LLM 适配 | `llm/` | 各厂商 OpenAI 兼容接口 |
| 可观测性 | `observability/` | 日志、OTel；FastAPI 自动埋点 |
| 数据库（可选） | `database/`、`db_repositories/` | 异步 SQLAlchemy 等（如产品查询） |

```mermaid
flowchart TB
  subgraph api [API Layer]
    documents["/api/documents"]
    chunks["/api/chunks"]
    kb["/api/kb"]
    search["/api/search /chat"]
    agent["/api/agent"]
  end
  subgraph parser [Parser Workflow]
    wf[run_parser_workflow_stream]
  end
  subgraph store [Knowledge Base]
    chroma[ChromaWriter]
    fts[FTSWriter]
    ret[Vector + BM25 + RRF + Rerank]
  end
  documents --> wf
  wf --> chroma
  wf --> fts
  search --> ret
  agent --> ret
  agent --> tools[Tools: Web Neo4j Postgres]
```

---

## 核心数据流

### 1. 文档入库（上传 → 解析 → 写入）

1. 客户端 **`POST /api/documents`**，上传文件正文（服务端按 **UTF-8** 解码，通常为 **Markdown** 源码）。  
2. 返回 **SSE** 流，内部调用 `run_parser_workflow_stream`（`parser/graph.py`）。  
3. 流水线结束时若产生 `DocumentChunk[]`，则并行写入：  
   - **ChromaDB**（`kb/writer/chroma_writer`）  
   - **SQLite FTS**（`kb/writer/fts_writer`）

若源文件为 PDF 等，需先在仓库外转为 UTF-8 Markdown 再上传；本仓库核心路径不包含 PDF 解析服务。

### 2. 检索与对话

- **`POST /api/search`**：`SearchService` → 混合检索（向量 + BM25 → RRF → 可选 Rerank）。  
- **`POST /api/chat`**：RAG 对话；另有 **`/api/chat/stream/start`** + **`GET /api/chat/stream/{session_id}`** 流式输出。

### 3. Agent

- **`POST /api/agent/chat`**：会话型 Agent（见 `api/agent/router.py` 与 `agent/`），可调用知识库检索、网络搜索、Neo4j、PostgreSQL 等工具（以当前 `agent/tools/` 注册为准）。

### 4. Chunk 与知识库管理

- Chunk 列表/详情/更新/删除：`/api/chunks`  
- 知识库统计与清空：`/api/kb/stats`、`DELETE /api/kb`

---

## 解析流水线（Parser Workflow）

有向图（`parser/graph.py`）概览：

```
Markdown → parse → clean → structure → slice → classify → [escalate] → enrich → transform → merge → DocumentChunk[]
```

各节点位于 `parser/nodes/`（`parse_node`、`clean_node`、`structure_node`、`slice_node`、`classify_node`、`escalate_node`、`enrich_node`、`transform_node`、`merge_node`）。

### 核心类型（`parser/models.py`）

- **`DocumentChunk`**：`chunk_id`、`doc_metadata`、`section_path`、`structure_type`、`semantic_type`、`content`、`raw_content`、`meta`  
- **`TypedSegment`**：`structure_type`（段落/列表/表/公式/标题等）与 `semantic_type`（metadata、scope、limit 等）双维度  
- **`WorkflowState`**：LangGraph 状态容器  

---

## API 一览

前缀均为 **`/api`**（FastAPI 应用在 `api/main.py` 中 `include_router(..., prefix="/api")`）。

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Documents | GET | `/documents` | 文档列表 |
| | POST | `/documents` | 上传（SSE，UTF-8 文本/Markdown） |
| | PATCH | `/documents/{doc_id}` | 更新文档元数据 |
| | DELETE | `/documents/clear` | 清空文档相关数据 |
| | DELETE | `/documents/{doc_id}` | 删除指定文档 |
| Chunks | GET | `/chunks` | 分页查询（支持 doc_id、semantic_type、section_path） |
| | GET | `/chunks/{chunk_id}` | 单个 chunk |
| | PUT | `/chunks/{chunk_id}` | 更新 chunk |
| | DELETE | `/chunks/{chunk_id}` | 删除 chunk |
| KB | GET | `/kb/stats` | 统计 |
| | DELETE | `/kb` | 清空知识库 |
| Search & Chat | POST | `/search` | 混合检索 |
| | POST | `/chat` | 对话 |
| | POST | `/chat/stream/start` | 开始流式会话 |
| | GET | `/chat/stream/{session_id}` | SSE 流式输出 |
| Agent | POST | `/agent/chat` | Agent 对话 |
| 可观测 | POST | `/logs` | 前端错误日志上报 |
| Product | GET | `/product` | 条形码查询产品（依赖 PostgreSQL 等） |

完整契约以 Swagger 为准。

---

## 环境变量

以下与 [`config.py`](config.py) 中 `Settings` 一致，可通过 **环境变量** 或 **`server/.env`** 覆盖（字段名不区分大小写）。

### 服务

| 变量 | 默认 | 说明 |
|------|------|------|
| `HOST` | `0.0.0.0` | 绑定地址 |
| `PORT` | `9999` | 端口 |
| `CORS_ORIGINS` | `["*"]` | CORS 来源列表 |

### LLM 通用 / 厂商

| 变量 | 默认 | 说明 |
|------|------|------|
| `LLM_API_KEY` | 空 | 通用 API Key |
| `LLM_BASE_URL` | 空 | OpenAI 兼容 Base URL |
| `DASHSCOPE_API_KEY` | 空 | 阿里云 DashScope |
| `DASHSCOPE_BASE_URL` | DashScope 兼容端点 | |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama |

### Parser 流水线

| 变量 | 默认 | 说明 |
|------|------|------|
| `PARSER_LLM_PROVIDER` | `openai` | 全局：`openai` / `dashscope` / `ollama` |
| `CLASSIFY_LLM_PROVIDER` 等 | 空 | 节点级覆盖，空则用全局 |
| `CLASSIFY_MODEL` | `qwen-turbo` | 分类节点 |
| `ESCALATE_MODEL` | `qwen-max` | 二次判断等 |
| `TRANSFORM_MODEL` | 空 | 不填则回退到 `ESCALATE_MODEL` |
| `DOC_TYPE_LLM_MODEL` | `qwen-max` | 文档类型推断 |
| `PARSER_STRUCTURED_MAX_RETRIES` | `2` | 结构化输出重试 |
| `PARSER_STRUCTURED_TIMEOUT_SECONDS` | `180` | 超时（秒） |
| `CHUNK_SOFT_MAX` / `CHUNK_HARD_MAX` / `CHUNK_MIN_SIZE` | 1500 / 3000 / 200 | 分块参数 |
| `CONFIDENCE_THRESHOLD` | `0.7` | 分类置信度阈值 |
| `SLICE_HEADING_LEVELS` | `[2,3,4]` | 标题层级 |
| `RULES_DIR` | `parser/rules` | 规则目录 |

### 嵌入与 Rerank

| 变量 | 默认 | 说明 |
|------|------|------|
| `EMBEDDING_MODEL` | `text-embedding-v3` | 嵌入模型名 |
| `EMBEDDING_LLM_PROVIDER` | 空 | 空则跟随 `PARSER_LLM_PROVIDER` |
| `RERANKER_MODEL` | `Qwen/Qwen3-Reranker-0.6B` | 重排序模型 |

### 存储

| 变量 | 默认 | 说明 |
|------|------|------|
| `CHROMA_PERSIST_DIR` | `./db` | Chroma 持久化目录 |
| `FTS_DB_PATH` | `./db/knowledge_base_fts.db` | SQLite 全文索引路径 |

### Neo4j

| 变量 | 默认 | 说明 |
|------|------|------|
| `NEO4J_URI` | `bolt://localhost:7687` | |
| `NEO4J_USERNAME` | `neo4j` | |
| `NEO4J_PASSWORD` | 空 | |
| `NEO4J_DATABASE` | `gb2760_2024` | |

### 对话 Agent

| 变量 | 默认 | 说明 |
|------|------|------|
| `CHAT_PROVIDER` | `openai` | |
| `CHAT_MODEL` | `qwen3-max-2026-01-23` | |
| `CHAT_BASE_URL` / `CHAT_API_KEY` | 空 | 覆盖默认连接 |
| `AGENT_SKILLS_PATH` | `agent/skills` | 相对 `server/` |
| `AGENT_MAX_ITERATIONS` | `10` | |
| `CHAT_TEMPERATURE` | `0.4` | |

### PostgreSQL

| 变量 | 默认 | 说明 |
|------|------|------|
| `POSTGRES_HOST` / `PORT` / `USER` / `PASSWORD` / `POSTGRES_DB` | localhost / 5432 / postgres / postgres / postgres | 分项 |
| `POSTGRES_URL` | 空 | **若设置则优先于分项**；格式如 `postgresql+psycopg://user:pass@host:port/dbname` |

### 可观测性

| 变量 | 默认 | 说明 |
|------|------|------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | OTLP 导出 |
| `OTEL_SERVICE_NAME` | `life-classics-server` | 服务名 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

---

## 规划与测试资产

- 实现计划与国标切分策略：`docs/plans/`  
- 自动化测试：`tests/`（`tests/api/`、`tests/core/parser_workflow/`、`tests/core/kb/`、`tests/core/agent/` 等）  
- 测试用 Markdown 与快照：`tests/assets/`、`tests/artifacts/`  

---

## 许可证

MIT License
