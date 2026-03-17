# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指引。

## 项目概览

本仓库为 monorepo，包含：
- `agent-server/` — Python FastAPI 后端：基于 RAG 的多工具 Agent，用于查询中国食品安全国家标准（GB 标准）
- `client/` — Next.js/React 前端（Turbo monorepo）

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
`agent-server/` 使用 **uv** 管理 Python 虚拟环境。所有 Python 相关命令在 `agent-server/` 目录下执行，且必须通过 `uv run` 调用：

```bash
# 所有 Python 命令格式：uv run python3 ...
cd agent-server
uv run python3 some_script.py

# 测试也通过 uv run 执行
uv run pytest tests/ -v
uv run pytest tests/core/kb/strategy/test_heading_strategy.py -v
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
uv run pytest tests/core/kb/strategy/test_heading_strategy.py -v
```


## 架构说明

### 核心数据结构

`app/core/document_chunk.py` 定义了 `DocumentChunk` —— 贯穿整个处理流水线的核心数据模型：
- `content_type`：18 个值的 `ContentType` 枚举（如 `scope`、`definition`、`formula`、`test_method`、`specification_table`、`reagent` 等）
- `section_path`：章节层级路径（如 `["3", "3.1"]`）
- `content`：字符串或结构化内容（表格行、公式变量）
- `markdown_id`：对应存储在 `markdown_db/` 中的原始 Markdown 文件引用

### 文档处理流水线

```
文件上传 → Import → Pre-parse → 切分策略 → ChromaDB + Neo4j
```

1. **Import**（`app/core/kb/imports/`）：PDF（经 MinerU HTTP 服务转换为 Markdown）、Markdown、JSON、Text
2. **Pre-parse**（`app/core/kb/pre_parse/`）：基于 LLM 对 PDF 进行结构推断
3. **切分策略**（`app/core/kb/strategy/`）：
   - `heading_strategy` — 按 `##`/`###` Markdown 标题切分
   - `text_strategy` — 固定大小切块
   - `table_strategy` — 提取表格并转换为自然语言
   - `structured_strategy` — LLM 引导的结构化切分
   - `parent_child_strategy` — 层级父子块
   - `doc_type` — 推断文档类型/分类
4. **存储**：ChromaDB（向量，持久化至 `chroma_db/`）+ Neo4j（图关系）

### Agent

`app/core/agent/factory.py` — `create_national_standard_agent()` 基于 Deep Agents + LangGraph 构建 Agent，注册了 `app/core/tools/` 中的工具：
- `knowledge_base` — ChromaDB 向量检索（含重排序）
- `web_search` — DuckDuckGo 搜索
- `document_type` — 推断 GB 标准分类
- `neo4j_query` — 图数据库查询
- `postgres_query` — SQL 查询

Agent 技能以 Markdown 形式定义在 `app/skills/`（由 Deep Agents 框架加载）。

### LLM 提供商

通过 `app/core/config.py`（Pydantic Settings，读取 `.env`）配置：
- **DashScope**（阿里通义千问）— 主要提供商，设置 `DASHSCOPE_API_KEY`
- **Ollama** — 本地模型，设置 `OLLAMA_BASE_URL`
- **OpenRouter** — 多模型代理

提供商和模型选择可通过环境变量在运行时完全配置。Provider 适配器见 `app/core/llm/`。

### API 端点

- `POST /api/doc/upload` — 上传文件并选择切分策略
- `GET /api/doc/documents` — 列出文档
- `GET /api/doc/chunks` — 带过滤条件的分页 Chunk 查询
- `POST /api/agent/chat` — 多工具 Agent 对话

### 关键配置（`app/core/config.py`）

所有配置项均支持环境变量覆盖。关键变量：
- `LLM_PROVIDER`、`CHAT_MODEL`、`EMBEDDING_MODEL`
- `DASHSCOPE_API_KEY`、`OLLAMA_BASE_URL`
- `NEO4J_URI`、`NEO4J_USERNAME`、`NEO4J_PASSWORD`
- `POSTGRES_URL`
- `MINERU_SERVICE_URL` — 外部 PDF→Markdown 转换服务
- `CHROMA_PERSIST_DIR`（默认：`chroma_db/`）、`MARKDOWN_DB_DIR`（默认：`markdown_db/`）

### 规划文档

`agent-server/docs/plans/` 包含详细的分阶段实现计划（基于 TDD）。实现新功能前请先阅读——系统针对 GB 标准制定了特定的切分和分类规则。

`agent-server/docs/assets/` 包含约 20 份 GB 食品安全标准的 Markdown 源文档。
