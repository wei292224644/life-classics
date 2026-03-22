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

    # ── DashScope 专用凭证 ────────────────────────────────────────────────────
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ── Ollama 连接 ───────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── Parser Workflow Provider 选择 ─────────────────────────────────────────
    PARSER_LLM_PROVIDER: str = "openai"  # 全局默认，可选 openai / dashscope / ollama
    CLASSIFY_LLM_PROVIDER: str = ""  # 节点级覆盖，空则使用全局默认
    ESCALATE_LLM_PROVIDER: str = ""
    TRANSFORM_LLM_PROVIDER: str = ""
    DOC_TYPE_LLM_PROVIDER: str = ""  # 对应 structure_node.py

    # ── 各用途模型 ──────────────────────────────────────────────────────────
    # parser workflow：classify_node（小模型，追求速度）
    CLASSIFY_MODEL: str = "qwen-turbo"
    # parser workflow：escalate_node（大模型，追求准确）
    ESCALATE_MODEL: str = "qwen-max"
    # parser workflow：transform_node llm_transform 策略（不填则 fallback 到 ESCALATE_MODEL）
    TRANSFORM_MODEL: str = ""
    # parser workflow：structure_node doc_type 推断兜底
    DOC_TYPE_LLM_MODEL: str = "qwen-max"

    # ── Parser Workflow Structured Output（Instructor）────────────────────────
    PARSER_STRUCTURED_MAX_RETRIES: int = 2
    PARSER_STRUCTURED_TIMEOUT_SECONDS: int = 180
    PARSER_STRUCTURED_TEMPERATURE: float = 0.0
    PARSER_STRUCTURED_LOG_PROMPT_PREVIEW: bool = False

    # ── Parser Workflow 参数 ────────────────────────────────────────────────
    CHUNK_SOFT_MAX: int = 1500
    CHUNK_HARD_MAX: int = 3000
    CHUNK_MIN_SIZE: int = 200  # 小于此值的 sibling 块会被累积合并，避免碎片 chunk
    CONFIDENCE_THRESHOLD: float = 0.7
    SLICE_HEADING_LEVELS: List[int] = [2, 3, 4]
    # 规则文件目录（运行时动态追加新规则）
    RULES_DIR: str = "parser/rules"

    # ── Embedding 配置 ────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_LLM_PROVIDER: str = ""  # 空则使用 PARSER_LLM_PROVIDER，支持 openai/dashscope/ollama
    

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

    # ── 对话Agent配置 ────────────────────────────────────────────────────────────
    CHAT_PROVIDER: str = "openai"
    CHAT_MODEL: str = "qwen3-max-2026-01-23"
    CHAT_BASE_URL: str = ""
    CHAT_API_KEY: str = ""
    AGENT_SKILLS_PATH: str = "agent/skills"   # 相对于 server/ 目录
    AGENT_MAX_ITERATIONS: int = 10
    CHAT_TEMPERATURE: float = 0.4

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


settings = Settings()
