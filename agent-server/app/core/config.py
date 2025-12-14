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
    QWEN_MODEL: str = "qwen-max"  # 可选: qwen-turbo, qwen-plus, qwen-max
    QWEN_EMBEDDING_MODEL: str = "text-embedding-v2"  # Qwen嵌入模型
    
    # ChromaDB配置
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"
    
    # 文档处理配置
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    SUPPORTED_EXTENSIONS: List[str] = [".pdf", ".txt", ".md", ".docx", ".pptx"]
    
    # 文档分割策略: "simple", "semantic", "sentence", "markdown", "hybrid", "structured"
    # simple: 简单分割（推荐用于纯文本）
    # semantic: 语义分割（推荐用于包含表格和公式的PDF）
    # sentence: 按句子分割（保持句子完整性）
    # markdown: Markdown格式分割（按标题分割）
    # hybrid: 混合策略（结合多种方法）
    # structured: 结构化分割（推荐用于包含表格和公式的PDF）
    SPLIT_STRATEGY: str = "simple"
    
    # Simple分割器配置
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # Semantic分割器配置（用于包含表格和公式的PDF）
    SEMANTIC_CHUNK_SIZE: int = 1000
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.7
    
    # Sentence分割器配置
    SENTENCE_CHUNK_SIZE: int = 1500
    SENTENCE_CHUNK_OVERLAP: int = 200
    
    # Markdown分割器配置
    MARKDOWN_SPLIT_HEADERS: List[str] = ["h1", "h2", "h3"]
    
    # Structured分割器配置（用于包含表格和公式的PDF，推荐）
    STRUCTURED_TEXT_CHUNK_SIZE: int = 900  # 普通文本块大小
    STRUCTURED_TEXT_CHUNK_OVERLAP: int = 150  # 普通文本块重叠
    STRUCTURED_FORMULA_CONTEXT: int = 2  # 公式前后保留的句子数
    STRUCTURED_SECTION_PATTERN: str = r"^\d+\s+[^\n]+"  # 章节标题模式
    
    # 父子Chunk配置（使用AutoMergingRetriever）
    PARENT_CHUNK_SIZE: int = 1500  # 父chunk大小（字符数，约1000-2000 tokens）
    CHILD_CHUNK_SIZE: int = 300  # 子chunk大小（字符数，约200-400 tokens）
    ENABLE_PARENT_CHILD: bool = False  # 是否启用父子chunk模式
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 9999
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

