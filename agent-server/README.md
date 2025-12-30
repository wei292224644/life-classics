# 个人知识库系统

基于 FastAPI + LangChain + ChromaDB 构建的智能知识库系统，支持多种文档格式导入、智能切分、向量存储和语义检索。

## 功能特性

- 📄 **多格式文档支持**：支持 PDF、Markdown、Text 等格式的文档导入
- 🔪 **智能切分策略**：提供 text、structured、table、heading、parent_child 等多种切分策略
- 🧠 **LLM 增强处理**：使用 LLM 进行文档结构分析和内容结构化转换
- 🔍 **OCR 支持**：自动识别图片型 PDF，使用 OCR 提取文本内容
- 📊 **向量存储与检索**：基于 ChromaDB 的向量存储，支持语义检索和重排序（Rerank）
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

创建 `.env` 文件（可选，也可直接在 `app/core/config.py` 中配置）：

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
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=knowledge_base
```

### 启动服务

```bash
python run.py
```

或使用 uvicorn 直接启动：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9999 --reload
```

服务启动后，访问：
- Web 界面：http://localhost:9999
- API 文档：http://localhost:9999/swagger

## 项目结构

```
agent-server/
├── app/
│   ├── api/                    # API 路由模块
│   │   ├── __init__.py
│   │   └── document.py         # 文档导入和管理 API
│   ├── core/                   # 核心功能模块
│   │   ├── config.py           # 应用配置
│   │   ├── document_chunk.py   # 文档块数据结构
│   │   ├── embeddings.py       # Embedding 模型管理
│   │   ├── file_converter.py   # 文件格式转换
│   │   ├── llm.py              # LLM 模型管理
│   │   ├── kb/                 # 知识库核心模块
│   │   │   ├── __init__.py
│   │   │   ├── imports/        # 文档导入模块
│   │   │   │   ├── import_pdf.py
│   │   │   │   ├── import_markdown.py
│   │   │   │   ├── import_text.py
│   │   │   │   └── import_json.py
│   │   │   ├── pre_parse/      # 预处理模块
│   │   │   │   ├── convert_to_structured.py  # PDF 转结构化 Markdown
│   │   │   │   └── ocr_step.py              # OCR 处理
│   │   │   ├── strategy/       # 切分策略模块
│   │   │   │   ├── text_strategy.py
│   │   │   │   ├── structured_strategy.py
│   │   │   │   ├── table_strategy.py
│   │   │   │   ├── heading_strategy.py
│   │   │   │   └── parent_child_strategy.py
│   │   │   └── vector_store/   # 向量存储模块
│   │   │       ├── __init__.py
│   │   │       ├── retriever.py
│   │   │       └── rerank.py
│   │   ├── providers/          # LLM 提供者实现
│   │   │   ├── base.py
│   │   │   ├── dashscope.py
│   │   │   ├── ollama.py
│   │   │   ├── openrouter.py
│   │   │   └── factory.py
│   │   └── tools/              # 工具模块
│   │       └── web_search.py
│   ├── web/                    # Web 界面
│   │   ├── main.py
│   │   ├── index.html
│   │   └── templates/          # HTML 模板
│   └── main.py                 # FastAPI 应用入口
├── chroma_db/                  # ChromaDB 数据目录
├── files/                      # 上传文件存储目录
├── markdown_cache/             # Markdown 缓存目录
├── pyproject.toml              # 项目配置
├── requirements.txt            # Python 依赖
├── run.py                      # 启动脚本
└── README.md                   # 项目文档
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
- **Text** (.txt)：纯文本文件
- **JSON** (.json)：暂未实现

### 切分策略

系统提供多种切分策略，可根据文档类型和需求选择：

- **`text`**（默认）：文本切分，按照段落、句子等文本单位进行切分
- **`structured`**：结构化切分，按照章节、小节、段落等结构进行切分。当导入 PDF 时，会通过 LLM 分析文档结构，再转化为 Markdown 格式，然后进行切分。`暂不支持 Text/JSON 格式文件`
- **`table`**：表格切分，按照表格、行、列等表格单位进行切分
- **`heading`**：标题切分，按照标题、副标题等标题单位进行切分
- **`parent_child`**：父子切分，按照父子关系进行切分

### 知识库导入流程

1. **文件上传**：用户通过 Web 界面或 API 上传文件
2. **格式识别**：系统识别文件格式并选择对应的导入器
3. **预处理**：
   - 如果是图片型 PDF，使用 OCR 提取文本
   - 如果选择 structured 策略，使用 LLM 将 PDF 转换为结构化 Markdown
4. **内容切分**：根据选择的切分策略对文档进行切分
5. **向量化存储**：将切分后的内容转换为向量并存储到 ChromaDB

## Content Type 说明

知识库系统支持多种内容类型（content_type），用于对文档内容进行语义分类和结构化存储。以下是所有支持的内容类型及其含义：

### 文档元信息类

- **`metadata`**：文档元信息，包括标准编号、标准名称、发布日期、适用对象等基本信息

### 适用范围类

- **`scope`**：适用范围，描述标准或文档的适用对象、应用领域等

### 定义类

- **`definition`**：概念、术语、常数定义，用于解释文档中使用的专业术语或常量

### 化学信息类

- **`chemical_formula`**：分子式，化学物质的分子式表示（如 C₄₀H₅₆）
- **`chemical_structure`**：结构式说明，包括"原文未给出结构图"的明确描述
- **`molecular_weight`**：相对分子质量，化学物质的相对分子质量数值

### 技术规范类

- **`specification_table`**：技术指标/限量/要求类表格，以结构化表格形式存储的技术规范
- **`specification_text`**：技术要求，非表格形式的文字性规范要求

### 检验方法类

- **`test_method`**：检验方法/测定步骤，流程性的检验操作描述
- **`identification_test`**：鉴别试验，用于识别和验证物质的方法
- **`chromatographic_method`**：色谱/光谱/顶空/UV-Vis 等仪器分析方法

### 实验条件类

- **`instrument`**：仪器与设备，实验或检验所需的仪器设备说明
- **`reagent`**：试剂与材料，实验或检验所需的试剂和材料清单

### 计算公式类

- **`calculation_formula`**：计算公式，包含公式本体和变量定义的计算公式

### 规则说明类

- **`general_rule`**：一般规定、通用规则，适用于整个文档或特定章节的通用规则
- **`note`**：注释、说明、补充性文字，包括"注：……"形式的补充说明

### 使用说明

在 Markdown 文档中，使用以下格式标注 content_type：

```markdown
【content_type: scope】
本标准适用于...

【content_type: specification_table】
| 项目 | 要求 | 检验方法 |
|------|------|----------|
| 色泽 | 暗红色至棕红色 | ... |
```

或者使用 fenced block 格式：

````markdown
```specification_table
| 项目 | 要求 |
|------|------|
| ... | ... |
```
````

系统会根据 content_type 对内容进行结构化解析和存储，便于后续的语义检索和知识推理。

## API 文档

启动服务后，访问 http://localhost:9999/swagger 查看完整的 API 文档。

主要 API 端点：

- `POST /api/doc/upload`：上传文档到知识库
- `GET /api/doc/documents`：获取文档列表
- `GET /api/doc/documents/{doc_id}`：获取文档详情
- `GET /api/doc/chunks`：获取文档块列表
- `GET /api/doc/chunks/{chunk_id}`：获取文档块详情
- `DELETE /api/doc/documents/{doc_id}`：删除文档

## 配置说明

主要配置项位于 `app/core/config.py`，支持通过环境变量或 `.env` 文件配置：

- **模型提供者**：可选择 DashScope、Ollama 或 OpenRouter
- **向量数据库**：ChromaDB 持久化目录和集合名称
- **文档处理**：支持的文件格式、最大文件大小等
- **OCR 配置**：OCR 语言、最小文本长度等
- **文本切分**：chunk_size、chunk_overlap 等参数

详细配置说明请参考 `app/core/config.py` 文件。

## 开发

### 运行开发服务器

```bash
python run.py
```

开发模式下会自动重载代码变更。

### 代码结构说明

- `app/core/kb/`：知识库核心模块，包含导入、预处理、切分、向量存储等功能
- `app/core/providers/`：LLM 提供者抽象和实现，支持多种模型服务
- `app/api/`：RESTful API 接口
- `app/web/`：Web 界面和模板

## 许可证

MIT License
