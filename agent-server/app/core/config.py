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
    LLM_PROVIDER: str = "ollama"  # "dashscope", "ollama", "openrouter"

    # DashScope配置
    DASHSCOPE_API_KEY: str = "sk-03f3eb5bc4cf446bafa1c76e762f65ad"

    # Ollama配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Chat配置
    CHAT_PROVIDER: str = "dashscope"
    CHAT_MODEL: str = "qwen3-max-2026-01-23"
    CHAT_TEMPERATURE: float = 0.4

    # OpenRouter配置
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-3.5-turbo"
    OPENROUTER_EMBEDDING_MODEL: str = "text-embedding-ada-002"

    # Reranker配置
    RERANKER_PROVIDER: str = "ollama"
    RERANKER_MODEL: str = "dengcao/Qwen3-Reranker-8B:Q5_K_M"
    RERANKER_TEMPERATURE: float = 0.4

    # Embedding配置
    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_MODEL: str = "qwen3-embedding:4b"

    # DOCUMENT_CONVERT配置
    DOCUMENT_CONVERT_PROVIDER: str = "ollama"
    DOCUMENT_CONVERT_MODEL: str = "qwen3:1.7b"

    # 文档Chunk配置
    DOCUMENT_STRUCTURE_PROVIDER: str = "dashscope"
    DOCUMENT_STRUCTURE_MODEL: str = "qwen3-max-2026-01-23"
    DOCUMENT_STRUCTURE_TEMPERATURE: float = 0.4
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    SUPPORTED_EXTENSIONS: List[str] = [".pdf", ".txt", ".md", ".docx", ".pptx"]
    MARKDOWN_CACHE_DIR: str = "./markdown_cache"

    # ChromaDB配置
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"
    
    # Markdown数据库配置
    MARKDOWN_PERSIST_DIR: str = "./markdown_db"
    MARKDOWN_COLLECTION_NAME: str = "markdown_base"

    # OCR配置
    ENABLE_OCR: bool = True
    OCR_LANG: str = "chi_sim+eng"
    OCR_MIN_TEXT_LENGTH: int = 10

    # 网络搜索配置
    ENABLE_WEB_SEARCH: bool = True
    SEARCH_PROVIDER: str = "duckduckgo"  # "duckduckgo", "tavily", "serper"
    TAVILY_API_KEY: str = ""
    SERPER_API_KEY: str = ""

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 9999

    # 文本切分配置
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 200
    CHUNK_SEPARATOR: str = "\n\n"
    CLEAN_TEXT_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
