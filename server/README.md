# 个人知识库系统

基于 FastAPI + LangChain + ChromaDB 构建的智能知识库系统，支持多种文档格式导入、智能切分、向量存储和语义检索。

## 功能特性

- 📄 **多格式文档支持**：支持 PDF（经 MinerU 转 Markdown）、Markdown、Text 等格式的文档导入
- 🔪 **智能切分策略**：PDF 按标题粗粒度切分；其他格式支持 text、structured、heading 等策略
- 📊 **向量存储与检索**：基于 ChromaDB 的向量存储，支持语义检索和重排序（Rerank）
- 🕸 **知识图谱**：Neo4j 存储文档与块关系（Document -[:CONTAINS]-> Chunk），便于扩展实体与关系
- 🤖 **Agent 模块**：基于 Deep Agents 的多工具编排，支持知识库检索、网络搜索、Neo4j/PostgreSQL 查询；接口：`/api/agent/chat`
- 🌐 **多模型提供者**：支持 DashScope（通义千问）、Ollama、OpenRouter 等多种 LLM 和 Embedding 提供者
- 🎨 **Web 界面**：提供友好的 Web 界面用于文档管理和查看
- 🔌 **RESTful API**：完整的 API 接口，支持集成到其他系统

## 技术栈

- **Web 框架**：FastAPI
- **LLM 框架**：LangChain
- **向量数据库**：ChromaDB
- **文档处理**：pypdf, pdfplumber, markdown, unstructured
- **OCR**：pytesseract, pdf2image
- **模型提供者**：DashScope, Ollama, OpenRouter

## 快速开始

### 环境要求

- Python >= 3.10
- 已安装 Tesseract OCR（用于 OCR 功能，可选）

### 安装依赖

使用 pip 安装：

```bash
pip install -r requirements.txt
```

或使用 uv（推荐）：

```bash
uv sync
```

### 配置环境变量

创建 `.env` 文件（可选，也可直接在 `server/config.py` 中配置）：

```env
# LLM 提供者配置
LLM_PROVIDER=ollama  # 可选: dashscope, ollama, openrouter
EMBEDDING_PROVIDER=ollama

# DashScope 配置
DASHSCOPE_API_KEY=your_api_key
QWEN_MODEL=qwen3-max-preview
QWEN_EMBEDDING_MODEL=text-embedding-v2

# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:latest
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b

# OpenRouter 配置
OPENROUTER_API_KEY=your_api_key
OPENROUTER_MODEL=openai/gpt-3.5-turbo
OPENROUTER_EMBEDDING_MODEL=text-embedding-ada-002

# Reranker 配置
RERANKER_PROVIDER=ollama
RERANKER_MODEL=dengcao/Qwen3-Reranker-8B:Q4_K_M

# ChromaDB 配置
CHROMA_PERSIST_DIR=./db
CHROMA_COLLECTION_NAME=knowledge_base

# MinerU 服务（PDF 转 Markdown，本地 Docker 等）
MINERU_SERVICE_URL=http://localhost:8000
MINERU_REQUEST_TIMEOUT=300

# Neo4j 知识图谱（RAG 用默认库；GB2760 按版本分库，如 gb2760_2024）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j
NEO4J_DATABASE=neo4j

# Agent（Deep Agents）
CHAT_PROVIDER=dashscope
CHAT_MODEL=qwen3-max-2026-01-23
AGENT_SKILLS_PATH=server/agent/skills
AGENT_MAX_ITERATIONS=10
```

### 启动服务

```bash
python run.py
```

或使用 uvicorn 直接启动：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 9999 --reload
```

服务启动后，访问：
- Web 界面：http://localhost:9999
- API 文档：http://localhost:9999/swagger

## 项目结构

```
server/                          # Python FastAPI 后端（uv workspace）
├── api/                         # FastAPI 入口和路由
│   ├── main.py                  # FastAPI 应用入口
│   ├── config.py                # API 层配置
│   ├── documents/               # 文档管理 API
│   ├── chunks/                  # Chunk 管理 API
│   ├── search/                  # 检索 API
│   ├── kb/                      # 知识库 API
│   └── agent/                   # Agent API
├── agent/                       # Agent 核心
│   ├── factory.py               # Agent 工厂
│   ├── food_safety_agent.py     # 食品安全助手
│   ├── skill_loader.py          # 技能加载器
│   ├── session_store.py         # 会话存储
│   ├── llm_adapter.py           # LLM 适配器
│   ├── tools/                   # Agent 工具
│   │   ├── knowledge_base.py    # 知识库检索
│   │   ├── web_search.py        # 网络搜索
│   │   ├── neo4j_query.py       # 图数据库查询
│   │   └── postgres_query.py    # SQL 查询
│   └── skills/                  # Agent Skills（Markdown）
│       ├── national-standard-rag/SKILL.md
│       ├── web-search/SKILL.md
│       ├── neo4j-graph/SKILL.md
│       └── postgres-query/SKILL.md
├── kb/                          # 知识库
│   ├── writer/                  # 写入（ChromaDB + 全文索引）
│   ├── retriever/              # 检索（向量 + BM25 + Reranker）
│   ├── embeddings.py            # 嵌入模型封装
│   └── clients.py               # ChromaDB 连接管理
├── parser/                      # 文档处理流水线
│   ├── models.py                # 核心数据模型
│   ├── graph.py                 # LangGraph 有向图
│   ├── nodes/                   # 各处理节点
│   │   ├── parse_node.py
│   │   ├── clean_node.py
│   │   ├── structure_node.py
│   │   ├── slice_node.py
│   │   ├── classify_node.py
│   │   ├── escalate_node.py
│   │   ├── enrich_node.py
│   │   ├── transform_node.py
│   │   └── merge_node.py
│   ├── rules/                   # 规则配置
│   └── structured_llm/          # 结构化 LLM 输出
├── llm/                         # LLM 提供商适配器
├── config.py                    # 全局配置
├── run.py                       # 启动脚本
├── pyproject.toml
└── README.md
```

## 知识库架构设计

### 知识库通用数据结构

每个文档块（chunk）采用以下数据结构：

```json
{
  "chunk_id": "chunk_id",        // Required: 块唯一标识
  "doc_id": "doc_id",            // Required: 文档唯一标识
  "doc_title": "doc_title",      // Optional: 文档标题
  "section_path": ["section_path"], // Optional: 章节路径
  "content_type": "content_type", // Optional: 内容类型
  "content": "content",          // Required: 内容
  "meta": {}                     // Optional: 元数据
}
```

### 支持的文档格式

- **PDF** (.pdf)：支持文本型和图片型 PDF，图片型 PDF 自动使用 OCR 提取
- **Markdown** (.md, .markdown)：支持标准 Markdown 格式

### 切分策略

系统提供多种切分策略，可根据文档类型和需求选择：

- **`structured`**：结构化切分，按照章节、小节、段落等结构进行切分。当导入 PDF 时，会通过 LLM 分析文档结构，再转化为 Markdown 格式，然后进行切分。
- **国标 Markdown 切分规范**：针对国家标准（单添加剂、检测方法、微生物检验等）的按业务单元切分与引用展开规则，见 `docs/plans/2026-03-02-chunking-strategy-spec.md`。

### 知识库导入流程

1. **文件上传**：用户通过 Web 界面或 API 上传文件
2. **格式识别**：系统识别文件格式并选择对应的导入器
3. **预处理**：
   - 如果是图片型 PDF，使用 OCR 提取文本
   - 如果选择 structured 策略，使用 LLM 将 PDF 转换为结构化 Markdown
4. **内容切分**：根据选择的切分策略对文档进行切分
5. **向量化存储**：将切分后的内容转换为向量并存储到 ChromaDB

## API 文档

启动服务后，访问 http://localhost:9999/swagger 查看完整的 API 文档。

主要 API 端点：

- **Agent**：`POST /api/agent/chat` — 多工具对话（知识库 / 网络 / Neo4j / PostgreSQL）
- `POST /api/doc/upload`：上传文档到知识库
- `GET /api/doc/documents`：获取文档列表
- `GET /api/doc/documents/{doc_id}`：获取文档详情
- `GET /api/doc/chunks`：获取文档块列表
- `GET /api/doc/chunks/{chunk_id}`：获取文档块详情
- `DELETE /api/doc/documents/{doc_id}`：删除文档

## 配置说明

主要配置项位于 `server/config.py`，支持通过环境变量或 `.env` 文件配置：

- **模型提供者**：可选择 DashScope、Ollama 或 OpenRouter
- **向量数据库**：ChromaDB 持久化目录和集合名称
- **Neo4j**：`NEO4J_DATABASE` 指定当前库；GB2760 按版本使用不同 database（见 `docs/plans/2026-03-02-knowledge-base-gb2760-strategy.md`、`docs/assets/neo4j_schema.cypher`）
- **文档处理**：支持的文件格式、最大文件大小等
- **OCR 配置**：OCR 语言、最小文本长度等
- **文本切分**：chunk_size、chunk_overlap 等参数

详细配置说明请参考 `server/config.py` 文件。

## 开发

### 运行开发服务器

```bash
python run.py
```

开发模式下会自动重载代码变更。

### 代码结构说明

- `server/kb/`：知识库核心模块，包含导入、预处理、切分、向量存储等功能
- `server/llm/`：LLM 提供者抽象和实现，支持多种模型服务
- `server/api/`：RESTful API 接口
- `server/agent/`：Agent 核心模块

## 许可证

MIT License
