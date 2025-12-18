"""
应用配置
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用设置"""

    # API配置
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # 模型提供者配置
    # LLM提供者选择: "dashscope", "ollama", "openrouter"
    LLM_PROVIDER: str = "ollama"
    # Embedding提供者选择: "dashscope", "ollama", "openrouter"
    # 可以独立配置，例如：LLM使用ollama，Embedding使用dashscope
    EMBEDDING_PROVIDER: str = "ollama"

    # Qwen/DashScope配置
    DASHSCOPE_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-max"  # 可选: qwen-turbo, qwen-plus, qwen-max
    QWEN_EMBEDDING_MODEL: str = "text-embedding-v2"  # Qwen嵌入模型

    # Ollama配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"  # Ollama服务地址
    OLLAMA_MODEL: str = "qwen3:latest"  # Ollama模型名称，如: llama2, mistral, qwen等
    OLLAMA_EMBEDDING_MODEL: str = "qwen3-embedding:4b"  # Ollama嵌入模型

    # OpenRouter配置
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-3.5-turbo"  # OpenRouter模型名称
    OPENROUTER_EMBEDDING_MODEL: str = "text-embedding-ada-002"  # OpenRouter嵌入模型

    # ChromaDB配置
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"

    # 文档处理配置
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    SUPPORTED_EXTENSIONS: List[str] = [".pdf", ".txt", ".md", ".docx", ".pptx"]

    # 文档分割策略: "simple" 或 "structured"
    # simple: 简单分割（适合常规纯文本）
    # structured: 结构化分割（针对表格、公式等复杂布局的PDF）
    SPLIT_STRATEGY: str = "structured"

    # Simple分割器配置
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Structured分割器配置（用于包含表格和公式的PDF，推荐）
    STRUCTURED_TEXT_CHUNK_SIZE: int = 900  # 普通文本块大小
    STRUCTURED_TEXT_CHUNK_OVERLAP: int = 150  # 普通文本块重叠
    STRUCTURED_FORMULA_CONTEXT: int = 2  # 公式前后保留的句子数
    STRUCTURED_SECTION_PATTERN: str = r"^\d+\s+[^\n]+"  # 章节标题模式

    # 父子Chunk配置（使用AutoMergingRetriever）
    # Dify风格的父子切分配置
    PARENT_SEPARATOR: str = "\n\n"  # 父层级分段标识符
    PARENT_CHUNK_SIZE: int = 1024  # 父层级分段最大长度（字符数）
    CHILD_SEPARATOR: str = "\n"  # 子块分段标识符
    CHILD_CHUNK_SIZE: int = 512  # 子块分段最大长度（字符数）
    ENABLE_PARENT_CHILD: bool = True  # 是否启用父子chunk模式

    # 网络搜索配置
    ENABLE_WEB_SEARCH: bool = True  # 是否启用网络搜索功能
    SEARCH_PROVIDER: str = "duckduckgo"  # 搜索提供者: "duckduckgo", "tavily", "serper"
    # Tavily Search API 配置（https://tavily.com）
    TAVILY_API_KEY: str = ""
    # Serper API 配置（https://serper.dev）
    SERPER_API_KEY: str = ""

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 9999

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
