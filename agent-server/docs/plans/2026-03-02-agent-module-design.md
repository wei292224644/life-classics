# 国家标准 RAG 服务 — Agent 模块重构设计

**日期**: 2026-03-02  
**目标**: 基于 [Deep Agents](https://github.com/langchain-ai/deepagents) 构建 Agent 模块，整合知识库 RAG、网络检索、Neo4j 图谱、PostgreSQL 查询，采用 Markdown Skills 与 MCP 扩展能力。

**前置设计**: 数据管道（PDF→MinerU→切分→Chroma+Neo4j）见 `docs/plans/2026-03-02-national-standard-rag-refactor-design.md`。

---

## 1. 目标与范围

| 项目 | 说明 |
|------|------|
| **Agent 定位** | 国家标准 RAG 服务的统一智能入口，根据用户问题自动选择并组合多种数据源 |
| **核心能力** | ① 知识库 RAG（Chroma 向量检索 + 重排） ② 网络检索（DuckDuckGo/Tavily/Serper） ③ Neo4j 图谱查询 ④ PostgreSQL 关系库查询 |
| **技术选型** | Deep Agents（LangChain + LangGraph）作为 Agent harness；Skills 用 Markdown（SKILL.md）定义；Tools 可经 MCP 暴露 |
| **与现有 Chat 关系** | 保留现有 `/chat` 作为「纯 RAG」入口；新增 `/agent` 作为 Agent 入口，支持多工具编排与流式输出 |

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              用户请求（/agent 或 /chat）                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                             │
                    ▼                                             ▼
            use_agent=false 或 /chat                    use_agent=true 或 /agent
                    │                                             │
                    ▼                                             ▼
┌───────────────────────────────┐               ┌───────────────────────────────────────┐
│   ChatService（现有）          │               │   AgentService（新增）                 │
│   纯 RAG：检索 → 上下文 → LLM  │               │   Deep Agents harness                 │
└───────────────────────────────┘               │   ├── Skills（SKILL.md 渐进加载）       │
                                                │   ├── Tools（RAG / Web / Neo4j / PG）  │
                                                │   └── 规划 / 子 Agent / 上下文管理      │
                                                └───────────────────────────────────────┘
                                                                    │
                                    ┌───────────────────────────────┼───────────────────────────────┐
                                    │                               │                               │
                                    ▼                               ▼                               ▼
                            ┌───────────────┐               ┌───────────────┐               ┌───────────────┐
                            │ 知识库 Tool   │               │ 网络检索 Tool │               │ Neo4j Tool    │
                            │ Chroma 检索   │               │ web_search    │               │ Cypher 查询   │
                            └───────────────┘               └───────────────┘               └───────────────┘
                                    │                               │                               │
                                    ▼                               ▼                               ▼
                            ┌───────────────┐               ┌───────────────┐               ┌───────────────┐
                            │ ChromaDB      │               │ DuckDuckGo /   │               │ Neo4j         │
                            │ (向量存储)     │               │ Tavily / Serper│               │ (图谱)        │
                            └───────────────┘               └───────────────┘               └───────────────┘
                                                                                                    │
                                                                                                    ▼
                                                                                            ┌───────────────┐
                                                                                            │ PostgreSQL   │
                                                                                            │ Tool (SQL)   │
                                                                                            └───────────────┘
```

---

## 3. 技术栈与依赖库

### 3.1 新增依赖（pyproject.toml）

```toml
# Agent 核心
"deepagents>=0.4.0",           # Deep Agents harness（含 LangGraph）
"langgraph>=0.2.0",           # 若 deepagents 未覆盖则显式声明

# 数据库驱动
"neo4j>=5.0.0",               # Neo4j 官方驱动
"asyncpg>=0.29.0",            # PostgreSQL 异步驱动（推荐）或 psycopg[binary]

# MCP（可选，用于统一工具暴露）
"langchain-mcp-adapters>=0.1.0",  # Deep Agents 支持的 MCP 适配
```

### 3.2 依赖总览

| 类别 | 库 | 用途 |
|------|-----|------|
| **Agent** | deepagents | Agent harness、规划、子 Agent、Skills、上下文管理 |
| **LLM** | langchain, langchain-openai, dashscope, langchain-ollama | 模型调用（与现有一致） |
| **向量** | langchain-chroma, chromadb | 知识库检索（现有） |
| **图谱** | neo4j | Neo4j Cypher 查询 |
| **关系库** | asyncpg 或 psycopg | PostgreSQL SQL 查询 |
| **网络** | ddgs, requests | 网络检索（现有 web_search） |
| **Web** | fastapi, uvicorn | API 服务（现有） |
| **MCP** | langchain-mcp-adapters | 可选，将 Tools 暴露为 MCP |

---

## 4. 项目文件结构（重构后）

```
agent-server/
├── app/
│   ├── main.py                      # FastAPI 入口（现有）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── document/                # 文档管理、上传、检索（现有）
│   │   │   ├── document.py
│   │   │   ├── models.py
│   │   │   └── services/
│   │   │       ├── chat_service.py      # 纯 RAG 对话（保留）
│   │   │       ├── document_service.py
│   │   │       ├── search_service.py
│   │   │       └── ...
│   │   └── agent/                   # 【新增】Agent API
│   │       ├── __init__.py
│   │       ├── router.py            # /agent 路由
│   │       └── models.py            # AgentRequest, AgentResponse
│   │
│   ├── core/
│   │   ├── config.py                # 配置（增加 NEO4J_*, POSTGRES_*, AGENT_*）
│   │   ├── document_chunk.py        # 现有
│   │   ├── llm/                     # 现有
│   │   ├── kb/                      # 知识库（现有 + MinerU 适配）
│   │   ├── kg/                      # 【新增】Neo4j 封装
│   │   │   ├── __init__.py
│   │   │   └── neo4j_store.py
│   │   ├── pdf/                     # 【新增】MinerU 适配
│   │   │   ├── __init__.py
│   │   │   └── mineru_adapter.py
│   │   ├── tools/                   # 工具（现有 + 扩展）
│   │   │   ├── __init__.py
│   │   │   ├── web_search.py        # 现有
│   │   │   ├── knowledge_base.py   # 【新增】RAG 检索 Tool
│   │   │   ├── neo4j_query.py      # 【新增】Neo4j Tool
│   │   │   └── postgres_query.py   # 【新增】PostgreSQL Tool
│   │   └── agent/                   # 【新增】Agent 核心
│   │       ├── __init__.py
│   │       ├── factory.py          # create_national_standard_agent()
│   │       └── llm_adapter.py      # 将现有 LLM 适配为 LangChain ChatModel
│   │
│   ├── skills/                      # 【新增】Agent Skills（Markdown）
│   │   ├── national-standard-rag/   # 国标知识库 Skill
│   │   │   └── SKILL.md
│   │   ├── web-search/              # 网络检索 Skill
│   │   │   └── SKILL.md
│   │   ├── neo4j-graph/             # Neo4j 图谱 Skill
│   │   │   └── SKILL.md
│   │   └── postgres-query/          # PostgreSQL 查询 Skill
│   │       └── SKILL.md
│   │
│   └── web/                         # 现有 Web 界面
│
├── docs/
│   └── plans/
│       ├── 2026-03-02-national-standard-rag-refactor-design.md
│       ├── 2026-03-02-national-standard-rag-implementation-plan.md
│       └── 2026-03-02-agent-module-design.md    # 本文档
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 5. Agent 模块详细设计

### 5.1 Agent 创建（factory.py）

```python
# app/core/agent/factory.py 核心逻辑示意

from deepagents import create_deep_agent
from app.core.agent.llm_adapter import get_langchain_chat_model
from app.core.tools import (
    get_knowledge_base_tool,
    get_web_search_tool,
    get_neo4j_tool,
    get_postgres_tool,
)

def create_national_standard_agent(
    skills_path: str = "app/skills",
    tools: list | None = None,
    **kwargs
):
    """创建国家标准 RAG Agent"""
    model = get_langchain_chat_model()  # 适配现有 DashScope/Ollama
    tools = tools or [
        get_knowledge_base_tool(),
        get_web_search_tool(),
        get_neo4j_tool(),
        get_postgres_tool(),
    ]
    return create_deep_agent(
        model=model,
        tools=tools,
        skills=[f"{skills_path}/"],
        system_prompt="你是国家标准 RAG 助手，负责解答食品安全、添加剂、国标等相关问题。",
        **kwargs
    )
```

### 5.2 LLM 适配（llm_adapter.py）

将现有 `app.core.llm` 的 `chat` 接口适配为 LangChain 的 `BaseChatModel`，以便 Deep Agents 使用。可通过 `langchain-openai` 的 `ChatOpenAI` 兼容模式（base_url 指向 DashScope）或自定义 `BaseChatModel` 封装现有 HTTP 调用。

### 5.3 Tools 设计

| Tool | 输入 | 输出 | 实现要点 |
|------|------|------|----------|
| **knowledge_base** | query: str, top_k: int | 检索到的文档片段文本 | 封装 `vector_store_manager.search_with_rerank`，返回格式化字符串 |
| **web_search** | query: str, num_results: int | 搜索结果摘要 | 复用现有 `app.core.tools.web_search` |
| **neo4j_query** | query: str（自然语言或 Cypher） | 查询结果文本 | 若为自然语言，可先调小模型生成 Cypher，再执行；或提供预定义查询模板 |
| **postgres_query** | query: str（自然语言或 SQL） | 查询结果文本 | 同上，Text-to-SQL 或模板；需严格只读、参数化，防注入 |

---

## 6. Skills 设计（SKILL.md）

遵循 [Agent Skills 规范](https://agentskills.io/specification) 与 [Deep Agents Skills 文档](https://docs.langchain.com/oss/python/deepagents/skills)。

### 6.1 国标知识库 Skill

**路径**: `app/skills/national-standard-rag/SKILL.md`

```markdown
---
name: national-standard-rag
description: 用于查询食品安全国家标准、食品添加剂（如 GB2760）、限量、适用范围、CNS/INS 号等知识库中已有的内容。当用户问及国标、添加剂、限量、适用范围时使用此技能。
allowed-tools: knowledge_base
---

# 国标知识库检索

## 概述

本技能用于从本地知识库中检索国家标准相关文档（如 GB2760 食品添加剂使用标准），回答关于添加剂限量、适用范围、CNS 号、INS 号等问题。

## 使用步骤

1. **提取检索关键词**：从用户问题中提取核心概念（如添加剂名称、食品分类、标准号）。
2. **调用 knowledge_base 工具**：使用 `knowledge_base` 工具，传入提炼后的查询语句，获取 top_k 条相关文档片段。
3. **整合与回答**：基于检索结果，准确引用来源（doc_title、section_path），给出简洁、有依据的回答。若知识库无相关内容，明确告知用户。
```

### 6.2 网络检索 Skill

**路径**: `app/skills/web-search/SKILL.md`

```markdown
---
name: web-search
description: 用于查询近期食品安全事件、最新法规修订、风险预警、召回信息等时效性内容。仅当问题涉及「最新」「近期」「最近」等时间敏感词时使用。
allowed-tools: web_search
---

# 网络检索

## 概述

本技能用于检索互联网上的时效性信息，如近期食品安全事件、法规更新、召回通报等。知识库中已有的静态内容应优先使用 national-standard-rag 技能。

## 使用步骤

1. **判断时效性**：确认用户问题是否涉及时间敏感信息。
2. **调用 web_search 工具**：传入精简的搜索关键词，获取结果摘要。
3. **筛选与整合**：选取与问题最相关的结果，注明来源与时间，给出回答。
```

### 6.3 Neo4j 图谱 Skill

**路径**: `app/skills/neo4j-graph/SKILL.md`

```markdown
---
name: neo4j-graph
description: 用于查询知识图谱中的文档-块关系、实体关系。当用户需要了解文档结构、块之间的关联、或图谱中存储的实体关系时使用。
allowed-tools: neo4j_query
---

# Neo4j 图谱查询

## 概述

本技能用于查询 Neo4j 中存储的文档与块的结构关系，以及后续扩展的实体关系（如添加剂-食品分类关联）。

## 使用步骤

1. **明确查询意图**：判断用户是否需要图谱结构信息（如某文档包含哪些块、某实体的关联实体）。
2. **调用 neo4j_query 工具**：传入自然语言描述或预定义查询类型，获取图谱查询结果。
3. **解释结果**：将图谱结果转化为用户可理解的文字说明。
```

### 6.4 PostgreSQL 查询 Skill

**路径**: `app/skills/postgres-query/SKILL.md`

```markdown
---
name: postgres-query
description: 用于查询 PostgreSQL 中存储的结构化业务数据。仅当用户明确需要查询数据库中的表格数据时使用。
allowed-tools: postgres_query
---

# PostgreSQL 查询

## 概述

本技能用于执行只读 SQL 查询，获取 PostgreSQL 中的业务数据。需确保查询为只读，且使用参数化防止注入。

## 使用步骤

1. **确认数据需求**：判断用户问题是否涉及数据库中的结构化数据。
2. **调用 postgres_query 工具**：传入自然语言或结构化查询请求，工具内部负责生成安全 SQL 并执行。
3. **格式化结果**：将查询结果整理为表格或列表形式呈现给用户。
```

---

## 7. API 设计

### 7.1 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/chat` | Agent 对话（非流式） |
| POST | `/api/agent/chat/stream` | Agent 流式对话 |
| GET | `/api/agent/health` | Agent 健康检查（可选） |

### 7.2 请求/响应模型

```python
# AgentRequest（与 ChatRequest 类似，可复用或扩展）
class AgentRequest(BaseModel):
    message: str
    conversation_history: list[dict] | None = None
    thread_id: str | None = None  # 用于 Deep Agents checkpointer
    config: dict | None = None   # 如 top_k、是否启用某工具等

# AgentResponse
class AgentResponse(BaseModel):
    content: str
    sources: list[SearchResult] | None = None  # 知识库来源
    tool_calls: list[dict] | None = None       # 本次调用的工具及结果摘要（可选）
```

### 7.3 与现有 /chat 的关系

- **`/api/doc/chat`**：保持现有逻辑，走 `ChatService`，纯 RAG，无工具编排。
- **`/api/agent/chat`**：走 `AgentService`，使用 Deep Agents，支持多工具与 Skills。
- 前端或客户端可根据场景选择调用 `/chat` 或 `/agent`。

---

## 8. 配置项（config.py 新增）

```python
# Agent
AGENT_SKILLS_PATH: str = "app/skills"
AGENT_MAX_ITERATIONS: int = 10  # 工具调用最大轮次

# Neo4j（与数据管道设计一致）
NEO4J_URI: str = "bolt://localhost:7687"
NEO4J_USER: str = "neo4j"
NEO4J_PASSWORD: str = "neo4j"

# PostgreSQL
POSTGRES_URI: str = "postgresql://user:pass@localhost:5432/dbname"
POSTGRES_READONLY: bool = True  # 仅允许只读查询
```

---

## 9. 数据流（Agent 单次请求）

1. 用户请求到达 `/api/agent/chat`。
2. `AgentService` 加载 `create_national_standard_agent()` 创建的 Agent（或复用单例）。
3. 调用 `agent.invoke({"messages": [...], "thread_id": "..."})`。
4. Deep Agents 根据 system prompt 与 Skills 的 description 做**渐进披露**：先匹配相关 Skill，再读取对应 `SKILL.md` 全文。
5. Agent 决定调用哪些 Tool（knowledge_base / web_search / neo4j_query / postgres_query），按需多轮调用。
6. 汇总 Tool 结果，生成最终回复。
7. 返回 `AgentResponse`（含 content、sources、可选 tool_calls）。

---

## 10. 错误处理与安全

| 场景 | 处理方式 |
|------|----------|
| Neo4j / PostgreSQL 不可用 | Tool 内捕获异常，返回友好提示，不中断 Agent；可配置跳过该 Tool |
| SQL / Cypher 注入风险 | 仅允许只读；使用参数化；可限制为预定义查询模板 |
| 工具调用超时 | 为各 Tool 设置 timeout；Deep Agents 支持中断与重试 |
| Agent 无限循环 | 通过 `max_iterations` 限制工具调用轮次 |

---

## 11. MCP 扩展（可选）

若需将 Tools 暴露给外部客户端（如 Cursor、其他 MCP 客户端）：

1. 为 knowledge_base、neo4j_query、postgres_query 各实现一个 **MCP Server**（或统一 Server 暴露多工具）。
2. 使用 `langchain-mcp-adapters` 将 MCP 工具转为 LangChain Tool，再传入 `create_deep_agent(tools=[...])`。
3. 本阶段可先不实现 MCP，仅用原生 LangChain Tools；后续再接入。

---

## 12. 实施顺序建议

1. **Phase 1**：完成数据管道重构（MinerU、按标题切分、Neo4j 写入）— 见 `2026-03-02-national-standard-rag-implementation-plan.md`。
2. **Phase 2**：实现 Agent 基础设施  
   - 安装 deepagents，实现 `llm_adapter`、`factory`；  
   - 实现 `knowledge_base`、`web_search`（复用）两 Tool；  
   - 创建 `national-standard-rag`、`web-search` 两 Skill；  
   - 实现 `/api/agent/chat`，验证 RAG + 网络检索编排。
3. **Phase 3**：接入 Neo4j 与 PostgreSQL  
   - 实现 `neo4j_query`、`postgres_query` Tool；  
   - 创建对应 Skills；  
   - 完善配置与错误处理。
4. **Phase 4**（可选）：MCP、流式优化、子 Agent 配置。

---

## 13. 参考链接

- [Deep Agents](https://github.com/langchain-ai/deepagents)
- [Deep Agents Skills](https://docs.langchain.com/oss/python/deepagents/skills)
- [Agent Skills 规范](https://agentskills.io/specification)
- [数据管道设计](docs/plans/2026-03-02-national-standard-rag-refactor-design.md)
