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
    DASHSCOPE_MODEL: str = "qwen3-max-preview"  # DashScope模型名称

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
    MARKDOWN_CACHE_DIR: str = "./markdown_cache"  # Markdown 缓存目录

    # OCR配置（用于处理图片型PDF）
    ENABLE_OCR: bool = True  # 是否启用OCR功能
    OCR_LANG: str = "chi_sim+eng"  # OCR语言，chi_sim=简体中文，eng=英文，可组合使用
    OCR_MIN_TEXT_LENGTH: int = 10  # 如果提取的文本长度小于此值，尝试使用OCR

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
