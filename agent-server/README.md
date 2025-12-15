# 个人知识库系统

基于 Python + FastAPI + LangChain + LlamaIndex + ChromaDB 开发的个人知识库系统。

## 功能特性

- 📄 **多格式文档支持**: 支持 PDF、Markdown、Word、PowerPoint、TXT 等格式
- 🔍 **智能检索**: 基于向量相似度的语义搜索
- 💾 **持久化存储**: 使用 ChromaDB 进行向量数据持久化
- 🚀 **RESTful API**: 提供完整的 REST API 接口
- 📊 **文档管理**: 支持文档上传、查询、删除等操作

## 技术栈

- **FastAPI**: 现代化的 Python Web 框架
- **LangChain**: LLM 应用开发框架
- **LlamaIndex**: 数据索引和检索框架
- **ChromaDB**: 开源向量数据库
- **多模型提供者支持**: 统一的模型提供者中间层，支持灵活配置
  - **DashScope/Qwen**: 阿里云通义千问大语言模型和嵌入模型
  - **Ollama**: 本地大语言模型服务
  - **OpenRouter**: 统一的 API 网关，支持多种模型（OpenAI、Anthropic 等）

## 项目结构

```
agent/
├── app/
│   ├── api/              # API 路由
│   │   ├── documents.py  # 文档管理接口
│   │   ├── query.py      # 查询接口
│   │   └── health.py     # 健康检查
│   ├── core/             # 核心模块
│   │   ├── config.py     # 配置管理
│   │   ├── vector_store.py  # 向量存储
│   │   ├── document_loader.py  # 文档加载
│   │   ├── embeddings.py  # 嵌入模型
│   │   ├── llm.py        # LLM 配置
│   │   └── providers/    # 模型提供者中间层
│   │       ├── base.py   # 提供者基类
│   │       ├── factory.py  # 提供者工厂
│   │       ├── dashscope.py  # DashScope 提供者
│   │       ├── ollama.py  # Ollama 提供者
│   │       ├── openrouter.py  # OpenRouter 提供者
│   │       └── utils.py  # 工具函数
│   └── main.py           # FastAPI 应用入口
├── main.py               # 旧入口（可删除）
├── pyproject.toml        # 项目配置
├── .env.example          # 环境变量示例
└── README.md             # 项目文档
```

## 安装步骤

### 1. 创建虚拟环境

```bash
cd agent
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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后，访问：

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 根路径: http://localhost:8000/

## API 使用示例

### 1. 上传文档

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@example.pdf" \
  -F "description=示例文档"
```

### 2. 查询知识库

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是机器学习？",
    "top_k": 5
  }'
```

### 3. 获取知识库信息

```bash
curl "http://localhost:8000/api/documents/info"
```

### 4. 清空所有文档

```bash
curl -X DELETE "http://localhost:8000/api/documents/clear"
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

主要配置项在 `app/core/config.py` 中：

- `CHUNK_SIZE`: 文档分块大小（默认 1000）
- `CHUNK_OVERLAP`: 分块重叠大小（默认 200）
- `MAX_FILE_SIZE`: 最大文件大小（默认 10MB）
- `SUPPORTED_EXTENSIONS`: 支持的文件类型

## 使用示例

### Python 脚本示例

项目包含 `example_usage.py` 示例脚本，演示如何使用 API：

```bash
# 安装 requests 库（如果还没有）
pip install requests

# 运行示例
python example_usage.py
```

### 使用 curl 命令

```bash
# 上传文档
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@example.pdf" \
  -F "description=示例文档"

# 查询知识库
curl -X POST "http://localhost:8000/api/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是机器学习？", "top_k": 5}'

# 获取知识库信息
curl "http://localhost:8000/api/documents/info"
```

## 模型提供者架构

系统采用统一的模型提供者中间层设计，支持灵活的配置和扩展：

### 核心特性

1. **独立配置**: LLM 和 Embedding 提供者可以独立选择
2. **易于扩展**: 通过实现基类接口即可添加新的提供者
3. **统一接口**: 所有提供者都兼容 LlamaIndex 接口
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
   - DashScope: `llama-index-llms-dashscope`, `llama-index-embeddings-dashscope`
   - Ollama: `llama-index-llms-ollama`, `llama-index-embeddings-ollama`
   - OpenRouter: `llama-index-llms-openai`, `llama-index-embeddings-openai`

3. **扩展新提供者**: 要实现新的提供者，只需：
   - 继承 `BaseLLMProvider` 或 `BaseEmbeddingProvider`
   - 实现 `create_instance()` 和 `validate_config()` 方法
   - 在 `ModelFactory` 中注册新提供者
2. **数据存储**: ChromaDB 数据存储在 `./chroma_db` 目录，删除此目录会清空所有数据
3. **临时文件**: 上传的文件会临时存储在 `./uploads` 目录，处理完成后自动删除
4. **CORS 配置**: 建议在生产环境中配置适当的 CORS 策略
5. **文件大小限制**: 默认最大文件大小为 10MB，可在配置中修改
6. **支持的格式**: PDF、Markdown、Word (.docx)、PowerPoint (.pptx)、TXT

## 许可证

MIT License
