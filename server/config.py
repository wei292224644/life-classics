"""
全局配置，从 .env 读取，通过 settings 单例访问。
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 服务器 ─────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 9999
    # CORS Origins: "*" 适用于所有平台（浏览器/H5/微信小程序/支付宝小程序/抖音小程序）。
    # 小程序容器内置了 CORS 处理，"*" 可满足所有平台的白名单需求。
    CORS_ORIGINS: list[str] = ["*"]

    # ── LLM 通用连接 ────────────────────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""  # OpenAI-compatible endpoint，空则用 SDK 默认

    # ── Anthropic 专用凭证（MiniMax Anthropic-compatible endpoint）─────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = ""  # 如 https://api.minimax.chat/v1

    # ── DashScope 专用凭证 ────────────────────────────────────────────────────
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ── Ollama 连接 ───────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── 各用途模型 ──────────────────────────────────────────────────────────
    DEFAULT_LLM_PROVIDER: str = "anthropic"  # LLM 调用 provider
    DEFAULT_MODEL: str = "MiniMax-2.7"  # Parser/Analyse/Parse 共用默认模型
    EMBEDDING_LLM_PROVIDER: str = "ollama"  # Embedding provider
    EMBEDDING_MODEL: str = "nomic-embed-text"  # Ollama 部署的嵌入模型

    # ── Chat Agent ────────────────────────────────────────────────────────────
    CHAT_PROVIDER: str = "anthropic"
    CHAT_MODEL: str = "MiniMax-2.7"
    CHAT_BASE_URL: str = ""
    CHAT_API_KEY: str = ""
    CHAT_TEMPERATURE: float = 0.4
    AGENT_SKILLS_PATH: str = "agent/skills"  # 相对于 server/ 目录
    AGENT_MAX_ITERATIONS: int = 10

    # ── LLM 节点最大并行数 ─────────────────────────────────────────────────
    LLM_MAX_CONCURRENCY: int = 10

    # ── Parser Workflow Structured Output──────────────────────────────
    PARSER_STRUCTURED_MAX_RETRIES: int = 2
    PARSER_STRUCTURED_TIMEOUT_SECONDS: int = 20
    PARSER_STRUCTURED_TEMPERATURE: float = 0.0
    PARSER_STRUCTURED_LOG_PROMPT_PREVIEW: bool = False

    # ── Parser Workflow 参数 ────────────────────────────────────────────────
    CHUNK_SOFT_MAX: int = 1500
    CHUNK_HARD_MAX: int = 3000
    CHUNK_MIN_SIZE: int = 200  # 小于此值的 sibling 块会被累积合并，避免碎片 chunk
    CONFIDENCE_THRESHOLD: float = 0.7
    SLICE_HEADING_LEVELS: List[int] = [2, 3, 4]
    # 规则文件目录（运行时动态追加新规则）
    RULES_DIR: str = "workflow_parser_kb/rules"

    # ── Neo4j 连接 ────────────────────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "gb2760_2024"

    # ── Reranker 配置 ────────────────────────────────────────────────────────
    RERANKER_MODEL: str = "Qwen/Qwen3-Reranker-0.6B"

    # ── 存储路径 ──────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./db"
    FTS_DB_PATH: str = "./db/knowledge_base_fts.db"

    # ── PostgreSQL 连接 ────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "postgres"
    POSTGRES_URL: str = ""  # 直接连接 URL，优先级高于上面的分项配置
    # 格式: postgresql+psycopg://user:password@host:port/dbname

    # ── 可观测性（OTel + 日志）────────────────────────────────────────────────
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    OTEL_SERVICE_NAME: str = "life-classics-server"
    LOG_LEVEL: str = "INFO"

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    ANALYSIS_TASK_TTL_SECONDS: int = 3600  # 终态后任务记录保留时长

    # ── OCR 服务 ────────────────────────────────────────────────────────────────
    OCR_SERVICE_URL: str = "http://localhost:8100"  # PaddleOCR-VL-1.5 内部地址
    OCR_TIMEOUT_SECONDS: int = 30

    # ── references 白名单（逗号分隔）────────────────────────────────────────────
    ANALYSIS_REFERENCES_ALLOWLIST: str = "GB 2760,GB 7718,GB 28050,GB 14880,GB 2762,GB 31650"

    # ── 系统写库用户 ID ─────────────────────────────────────────────────────────
    SYSTEM_USER_ID: str = "00000000-0000-0000-0000-000000000001"

    # ── food_id 模糊匹配置信度阈值 ──────────────────────────────────────────────
    FOOD_NAME_MATCH_THRESHOLD: float = 0.80
    
    
    


settings = Settings()
