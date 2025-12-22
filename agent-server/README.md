# 个人知识库系统

基于 Python + FastAPI + LangChain + ChromaDB 开发的个人知识库系统。

## 功能特性

- 📄 **多格式文档支持**: 支持 PDF、Markdown、Word、PowerPoint、TXT 等格式
- 🔍 **智能检索**: 基于向量相似度的语义搜索，支持父子 chunk 结构
- 💾 **持久化存储**: 使用 ChromaDB 进行向量数据持久化，SQLite 存储父文档
- 🚀 **RESTful API**: 提供完整的 REST API 接口
- 📊 **文档管理**: 支持文档上传、查询、删除等操作
- 💬 **多轮对话**: 基于知识库的智能对话，支持上下文记忆
- 🌐 **网络搜索**: 集成网络搜索工具（DuckDuckGo、Tavily、Serper），补充知识库信息
- 🔤 **AI 翻译**: 支持中英文双向翻译
- 🖥️ **Web UI**: 提供浏览器界面，方便浏览和查看知识库数据
- 📸 **OCR 支持**: 支持图片型 PDF 的 OCR 识别
- 📦 **批量导入**: 支持批量导入文档到知识库

## 技术栈

- **FastAPI**: 现代化的 Python Web 框架
- **LangChain**: 数据索引和检索框架
- **ChromaDB**: 开源向量数据库
- **SQLite**: 父文档存储
- **多模型提供者支持**: 统一的模型提供者中间层，支持灵活配置
  - **DashScope/Qwen**: 阿里云通义千问大语言模型和嵌入模型
  - **Ollama**: 本地大语言模型服务
  - **OpenRouter**: 统一的 API 网关，支持多种模型（OpenAI、Anthropic 等）

## 项目结构

```
agent-server/
├── app/
│   ├── api/              # API 路由
│   │   ├── documents.py  # 文档管理接口
│   │   ├── query.py      # 查询接口
│   │   ├── chat.py       # 对话接口
│   │   ├── translate.py  # 翻译接口
│   │   └── health.py     # 健康检查
│   ├── core/             # 核心模块
│   │   ├── config.py     # 配置管理
│   │   ├── vector_store.py  # 向量存储
│   │   ├── parent_store.py  # 父文档存储（SQLite）
│   │   ├── document_loader.py  # 文档加载
│   │   ├── embeddings.py  # 嵌入模型
│   │   ├── llm.py        # LLM 配置
│   │   ├── providers/    # 模型提供者中间层
│   │   │   ├── base.py   # 提供者基类
│   │   │   ├── factory.py  # 提供者工厂
│   │   │   ├── dashscope.py  # DashScope 提供者
│   │   │   ├── ollama.py  # Ollama 提供者
│   │   │   ├── openrouter.py  # OpenRouter 提供者
│   │   │   └── utils.py  # 工具函数
│   │   └── tools/        # 工具模块
│   │       └── web_search.py  # 网络搜索工具
│   ├── web/              # Web UI
│   │   ├── chroma_viewer.py  # ChromaDB 数据查看器
│   │   └── templates/    # HTML 模板
│   └── main.py           # FastAPI 应用入口
├── files/                # 文档存储目录（可选）
├── import_files.py       # 批量导入脚本
├── view_chunks.py        # 查看 chunks 工具
├── view_all_chunks.py    # 查看所有 chunks 工具
├── run.py                # 启动脚本
├── pyproject.toml        # 项目配置
├── requirements.txt      # 依赖列表
├── .env.example          # 环境变量示例
└── README.md             # 项目文档
```

## 安装步骤

### 1. 创建虚拟环境

```bash
cd agent-server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安装依赖

使用 pip 安装（推荐）：

```bash
pip install -r requirements.txt
```

或使用项目安装：

```bash
pip install -e .
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置模型提供者：

**重要说明：**
- `LLM_PROVIDER` 和 `EMBEDDING_PROVIDER` 可以**独立配置**
- 例如：LLM 使用 Ollama（本地），Embedding 使用 DashScope（云端）
- 支持的提供者：`dashscope`、`ollama`、`openrouter`

**方式一：使用 DashScope/Qwen（云端）**

```env
LLM_PROVIDER=dashscope
EMBEDDING_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_dashscope_api_key_here
QWEN_MODEL=qwen-turbo
QWEN_EMBEDDING_MODEL=text-embedding-v2
```

> 注意：DashScope API Key 可以在阿里云控制台获取：https://dashscope.console.aliyun.com/

**方式二：使用 Ollama（本地）**

首先确保已安装并启动 Ollama 服务：

```bash
# 安装 Ollama（如果还没有）
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# 启动 Ollama 服务
ollama serve

# 在另一个终端拉取模型（例如 llama2 和 embedding 模型）
ollama pull llama2
ollama pull qwen3-embedding:4b  # 或其他 embedding 模型
```

然后在 `.env` 文件中配置：

```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b
```

**方式三：使用 OpenRouter（统一 API 网关）**

OpenRouter 支持多种模型（OpenAI、Anthropic、Google 等）：

```env
LLM_PROVIDER=openrouter
EMBEDDING_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openai/gpt-3.5-turbo
OPENROUTER_EMBEDDING_MODEL=text-embedding-ada-002
```

> 注意：
> - OpenRouter API Key 可以在 https://openrouter.ai/ 获取
> - 支持的模型列表：https://openrouter.ai/models
> - 模型名称格式：`provider/model-name`，如 `openai/gpt-4`、`anthropic/claude-3-opus`

**混合配置示例：LLM 使用 Ollama，Embedding 使用 DashScope**

```env
# LLM 使用本地 Ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Embedding 使用云端 DashScope
EMBEDDING_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_dashscope_api_key_here
QWEN_EMBEDDING_MODEL=text-embedding-v2
```

> 提示：
> - Ollama 支持多种 LLM 模型，如 `llama2`、`mistral`、`qwen` 等。使用前需要先通过 `ollama pull <model_name>` 下载模型。
> - Ollama 也支持多种 embedding 模型，如 `qwen3-embedding:4b`、`nomic-embed-text` 等。同样需要先通过 `ollama pull <embedding_model_name>` 下载。

### 4. 启动服务

方式一：使用启动脚本

```bash
python run.py
```

方式二：使用 uvicorn 直接启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 9999
```

服务启动后，访问：

- API 文档: http://localhost:9999/docs
- Swagger UI: http://localhost:9999/swagger
- 健康检查: http://localhost:9999/api/health
- Web UI (ChromaDB 查看器): http://localhost:9999/web/
- 根路径: http://localhost:9999/

## API 使用示例

### 1. 上传文档

```bash
curl -X POST "http://localhost:9999/api/documents/upload" \
  -F "file=@example.pdf" \
  -F "description=示例文档"
```

### 2. 批量上传目录

```bash
curl -X POST "http://localhost:9999/api/documents/upload-directory" \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "./files",
    "skip_existing": true
  }'
```

### 3. 查询知识库

```bash
curl -X POST "http://localhost:9999/api/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是机器学习？",
    "top_k": 5
  }'
```

### 4. 多轮对话

```bash
curl -X POST "http://localhost:9999/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请介绍一下机器学习的基本概念",
    "top_k": 5
  }'
```

### 5. AI 翻译

```bash
# 英文转中文
curl -X POST "http://localhost:9999/api/translate/" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "direction": "en_to_zh"
  }'

# 中文转英文
curl -X POST "http://localhost:9999/api/translate/" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，世界！",
    "direction": "zh_to_en"
  }'

# 自动检测语言并翻译
curl -X POST "http://localhost:9999/api/translate/auto" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!"
  }'
```

### 6. 获取知识库信息

```bash
curl "http://localhost:9999/api/documents/info"
```

### 7. 获取文档 chunks

```bash
# 获取所有文档的 chunks
curl "http://localhost:9999/api/documents/chunks"

# 获取指定文件的 chunks
curl "http://localhost:9999/api/documents/chunks/example.pdf"
```

### 8. 清空所有文档

```bash
curl -X DELETE "http://localhost:9999/api/documents/clear"
```

### 9. 健康检查

```bash
curl "http://localhost:9999/api/health"
```

## Web UI

系统提供了基于浏览器的 Web UI，方便查看和管理知识库数据：

### 访问 Web UI

启动服务后，访问以下地址：

- **主页**: http://localhost:9999/web/
- **文件列表**: http://localhost:9999/web/files
- **Chunks 列表**: http://localhost:9999/web/chunks

### 功能特性

- 📁 **文件浏览**: 查看所有已导入的文档
- 📄 **Chunk 查看**: 查看文档的分块内容
- 🔍 **搜索功能**: 在 Web UI 中搜索文档和 chunks
- 📊 **详细信息**: 查看文档和 chunk 的元数据信息

## 工具脚本

项目提供了多个工具脚本，方便批量操作和查看数据：

### 批量导入脚本 (`import_files.py`)

用于批量导入目录下的文档到知识库：

```bash
# 导入 files 目录下的所有 PDF
python import_files.py

# 从指定索引开始导入
python import_files.py --start-index 10 --batch-size 5

# 导入单个文件
python import_files.py --single-file example.pdf

# 跳过已存在的文件
python import_files.py --skip-existing
```

### 查看 Chunks 脚本

- `view_chunks.py`: 查看指定文件的 chunks
- `view_all_chunks.py`: 查看所有文档的 chunks

```bash
# 查看指定文件的 chunks
python view_chunks.py example.pdf

# 查看所有文档的 chunks
python view_all_chunks.py
```

## 开发

### 代码格式

项目使用标准的 Python 代码风格，建议使用 `black` 和 `flake8` 进行代码格式化。

### 测试

```bash
# 运行测试（需要先编写测试文件）
pytest
```

## 配置说明

主要配置项在 `app/core/config.py` 中，可通过环境变量或 `.env` 文件配置：

### 文档处理配置

- `CHUNK_SIZE`: 文档分块大小（默认 1000）
- `CHUNK_OVERLAP`: 分块重叠大小（默认 200）
- `MAX_FILE_SIZE`: 最大文件大小（默认 10MB）
- `SUPPORTED_EXTENSIONS`: 支持的文件类型
- `SPLIT_STRATEGY`: 文档分割策略，`simple` 或 `structured`（默认 `structured`）
- `ENABLE_PARENT_CHILD`: 是否启用父子 chunk 模式（默认 `True`）
  - `PARENT_CHUNK_SIZE`: 父层级分段大小（默认 1024）
  - `CHILD_CHUNK_SIZE`: 子块分段大小（默认 512）

### OCR 配置

- `ENABLE_OCR`: 是否启用 OCR 功能（默认 `True`）
- `OCR_LANG`: OCR 语言，如 `chi_sim+eng`（简体中文+英文）
- `OCR_MIN_TEXT_LENGTH`: 如果提取的文本长度小于此值，尝试使用 OCR（默认 10）

### 网络搜索配置

- `ENABLE_WEB_SEARCH`: 是否启用网络搜索功能（默认 `True`）
- `SEARCH_PROVIDER`: 搜索提供者，可选 `duckduckgo`、`tavily`、`serper`（默认 `duckduckgo`）
- `TAVILY_API_KEY`: Tavily Search API 密钥（可选）
- `SERPER_API_KEY`: Serper API 密钥（可选）

### 服务器配置

- `HOST`: 服务器地址（默认 `0.0.0.0`）
- `PORT`: 服务器端口（默认 `9999`）
- `CORS_ORIGINS`: CORS 允许的源列表

## 使用示例

### Python 脚本示例

项目包含 `example_usage.py` 示例脚本，演示如何使用 API：

```bash
# 安装 requests 库（如果还没有）
pip install requests

# 运行示例
python example_usage.py
```

## 模型提供者架构

系统采用统一的模型提供者中间层设计，支持灵活的配置和扩展：

### 核心特性

1. **独立配置**: LLM 和 Embedding 提供者可以独立选择
2. **易于扩展**: 通过实现基类接口即可添加新的提供者
3. **统一接口**: 所有提供者都兼容 LangChain 接口
4. **单例缓存**: 自动缓存实例，避免重复创建

### 支持的提供者

- **DashScope/Qwen**: 阿里云通义千问
  - 获取 API Key: https://dashscope.console.aliyun.com/
  - LLM 模型: qwen-turbo、qwen-plus、qwen-max
  - Embedding 模型: text-embedding-v2

- **Ollama**: 本地大语言模型服务
  - 安装: https://ollama.com/
  - 默认地址: http://localhost:11434
  - LLM 模型: llama2、mistral、qwen 等（需先 `ollama pull`）
  - Embedding 模型: qwen3-embedding:4b、nomic-embed-text 等（需先 `ollama pull`）

- **OpenRouter**: 统一的 API 网关
  - 获取 API Key: https://openrouter.ai/
  - 支持多种模型: OpenAI、Anthropic、Google 等
  - 模型列表: https://openrouter.ai/models

### 验证提供者配置

使用 Python 脚本验证配置：

```python
from app.core.providers.utils import print_provider_status, validate_all_providers

# 打印当前状态
print_provider_status()

# 验证所有配置的提供者
results = validate_all_providers()
print(results)
```

## 注意事项

1. **提供者配置**: LLM 和 Embedding 提供者可以独立配置
   - 例如：LLM 使用本地 Ollama，Embedding 使用云端 DashScope
   - 配置项：`LLM_PROVIDER` 和 `EMBEDDING_PROVIDER`

2. **依赖安装**: 不同提供者需要不同的依赖包
   - DashScope: 使用 `dashscope` SDK
   - Ollama: 使用 `langchain-ollama`
   - OpenRouter: 使用 `langchain-openai`（兼容 OpenAI API）

3. **扩展新提供者**: 要实现新的提供者，只需：
   - 继承 `BaseLLMProvider` 或 `BaseEmbeddingProvider`
   - 实现 `create_instance()` 和 `validate_config()` 方法
   - 在 `ModelFactory` 中注册新提供者

4. **数据存储**: 
   - ChromaDB 数据存储在 `./chroma_db` 目录，删除此目录会清空所有向量数据
   - 父文档数据存储在 `./parent_chunks.db`（SQLite），删除此文件会清空所有父文档数据

5. **临时文件**: 上传的文件会临时存储在 `./uploads` 目录，处理完成后自动删除

6. **CORS 配置**: 建议在生产环境中配置适当的 CORS 策略

7. **文件大小限制**: 默认最大文件大小为 10MB，可在配置中修改

8. **支持的格式**: PDF、Markdown、Word (.docx)、PowerPoint (.pptx)、TXT

9. **OCR 功能**: 
   - 需要安装 Tesseract OCR 引擎
   - macOS: `brew install tesseract tesseract-lang`
   - Linux: `sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim`
   - Windows: 从 [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装
   - 详细配置请参考 `OCR_SETUP.md`

10. **网络搜索**: 
    - 默认使用 DuckDuckGo（免费，无需 API 密钥）
    - 可选配置 Tavily 或 Serper API（需要 API 密钥）
    - 在对话 API 中，如果知识库中没有相关信息，会自动调用网络搜索

11. **父子 Chunk 模式**: 
    - 启用后，系统会将文档分为父 chunk 和子 chunk
    - 向量库只存储子 chunk，避免重复
    - 父 chunk 存储在 SQLite 中，用于 Web UI 展示和检索回溯
    - 推荐启用此模式以获得更好的检索效果

## 许可证

MIT License
