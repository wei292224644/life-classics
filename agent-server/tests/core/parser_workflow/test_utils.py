import logging
import os
from pathlib import Path
from typing import Tuple

import pytest

# 用于 parser_workflow 测试的 logger 命名空间，便于统一配置
LOG_NAMESPACE = "parser_workflow"


def setup_parser_workflow_logging(
    level: str | int | None = None,
    format_string: str | None = None,
) -> None:
    """
    配置 parser_workflow 测试的日志输出，便于调试。
    - 从环境变量 PARSER_WORKFLOW_LOG_LEVEL 读取级别（默认 INFO），可选 DEBUG / INFO / WARNING / ERROR。
    - 若未配置过 root logger 的 handler，则添加 StreamHandler 和统一格式。
    在 tests/core/parser_workflow/conftest.py 中自动调用；也可在单测中手动调用。
    """
    if level is None:
        level = os.environ.get("PARSER_WORKFLOW_LOG_LEVEL", "INFO").upper()
    if isinstance(level, str):
        level = getattr(logging, level, logging.INFO)

    if format_string is None:
        format_string = (
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    date_fmt = "%H:%M:%S"

    root = logging.getLogger()
    # 避免重复添加 handler（多次运行 pytest 或重复调用时）
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(format_string, datefmt=date_fmt)
        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    返回属于 parser_workflow 命名空间的 logger，会继承 conftest 中配置的日志级别和 handler。
    用法: logger = get_logger("classify_node_real_llm")
    """
    return logging.getLogger(f"{LOG_NAMESPACE}.{name}")


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_env_if_exists() -> None:
    """
    从项目根目录读取 .env，将其中的 KEY=VALUE 注入到 os.environ（不覆盖已有环境变量）。
    主要用于在本地运行真实 LLM 测试时方便加载密钥。
    """
    project_root = get_project_root()
    env_path = project_root / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def ensure_llm_api_key() -> None:
    """
    确保 LLM_API_KEY 已设置；否则跳过当前测试模块。
    真实 LLM 节点测试应在 module 级别或 autouse fixture 中调用此函数。
    """
    if not os.environ.get("LLM_API_KEY"):
        load_env_if_exists()

    if not os.environ.get("LLM_API_KEY"):
        pytest.skip("环境变量 LLM_API_KEY 未设置，跳过依赖真实 LLM 的测试")


def load_sample_markdown() -> Tuple[str, Path]:
    """
    加载 parser_workflow 使用的示例 GB 标准 Markdown 文档。
    返回 (md_content, asset_path)。
    """
    asset_path = (
        Path(__file__)
        .resolve()
        .parents[2]
        / "assets"
        / "《食品安全国家标准 食品添加剂 天门冬酰苯丙氨酸甲酯（又名阿斯巴甜）》（GB 1886.47-2016）第1号修改单.md"
    )
    md_content = asset_path.read_text(encoding="utf-8")
    return md_content, asset_path


def get_rules_dir() -> Path:
    """
    返回 parser_workflow 使用的规则目录路径。
    """
    project_root = get_project_root()
    return project_root / "app" / "core" / "parser_workflow" / "rules"

