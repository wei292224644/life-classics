"""
全局配置，从 .env 读取，通过 settings 单例访问。
"""

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

    # ── LLM 通用连接 ────────────────────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""          # OpenAI-compatible endpoint，空则用 SDK 默认

    # ── DashScope 专用凭证 ────────────────────────────────────────────────────
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ── Ollama 连接 ───────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── Parser Workflow Provider 选择 ─────────────────────────────────────────
    PARSER_LLM_PROVIDER: str = "openai"    # 全局默认，可选 openai / dashscope / ollama
    CLASSIFY_LLM_PROVIDER: str = ""        # 节点级覆盖，空则使用全局默认
    ESCALATE_LLM_PROVIDER: str = ""
    TRANSFORM_LLM_PROVIDER: str = ""
    DOC_TYPE_LLM_PROVIDER: str = ""        # 对应 structure_node.py

    # ── 各用途模型 ──────────────────────────────────────────────────────────
    # parser workflow：classify_node（小模型，追求速度）
    CLASSIFY_MODEL: str = "qwen-turbo"
    # parser workflow：escalate_node（大模型，追求准确）
    ESCALATE_MODEL: str = "qwen-max"
    # parser workflow：transform_node llm_transform 策略（不填则 fallback 到 ESCALATE_MODEL）
    TRANSFORM_MODEL: str = ""
    # parser workflow：structure_node doc_type 推断兜底
    DOC_TYPE_LLM_MODEL: str = "qwen-max"

    # ── Parser Workflow 参数 ────────────────────────────────────────────────
    CHUNK_SOFT_MAX: int = 1500
    CHUNK_HARD_MAX: int = 3000
    CONFIDENCE_THRESHOLD: float = 0.7
    # 规则文件目录（运行时动态追加新规则）
    RULES_DIR: str = "app/core/parser_workflow/rules"

    # ── 存储路径 ────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    MARKDOWN_DB_DIR: str = "./markdown_db"


settings = Settings()
