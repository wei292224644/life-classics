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
    
    # Qwen/DashScope配置
    DASHSCOPE_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-turbo"  # 可选: qwen-turbo, qwen-plus, qwen-max
    QWEN_EMBEDDING_MODEL: str = "text-embedding-v2"  # Qwen嵌入模型
    
    # ChromaDB配置
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"
    
    # 文档处理配置
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    SUPPORTED_EXTENSIONS: List[str] = [".pdf", ".txt", ".md", ".docx", ".pptx"]
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 9999
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

