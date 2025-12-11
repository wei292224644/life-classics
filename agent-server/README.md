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
- **Qwen (DashScope)**: 阿里云通义千问大语言模型和嵌入模型

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
│   │   └── llm.py        # LLM 配置
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

编辑 `.env` 文件，设置你的 DashScope API Key（用于Qwen模型）：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
QWEN_MODEL=qwen-turbo
QWEN_EMBEDDING_MODEL=text-embedding-v2
```

> 注意：DashScope API Key 可以在阿里云控制台获取：https://dashscope.console.aliyun.com/

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

## 注意事项

1. **DashScope API Key**: 需要有效的 DashScope API Key 才能使用 Qwen 模型和嵌入功能
   - 获取地址：https://dashscope.console.aliyun.com/
   - 支持的模型：qwen-turbo、qwen-plus、qwen-max
   - 嵌入模型：text-embedding-v2
2. **数据存储**: ChromaDB 数据存储在 `./chroma_db` 目录，删除此目录会清空所有数据
3. **临时文件**: 上传的文件会临时存储在 `./uploads` 目录，处理完成后自动删除
4. **CORS 配置**: 建议在生产环境中配置适当的 CORS 策略
5. **文件大小限制**: 默认最大文件大小为 10MB，可在配置中修改
6. **支持的格式**: PDF、Markdown、Word (.docx)、PowerPoint (.pptx)、TXT

## 许可证

MIT License
