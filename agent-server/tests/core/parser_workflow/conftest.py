"""
parser_workflow 测试的 conftest：统一启用日志，便于调试。
- 运行本目录下任意测试时，会自动配置日志（级别由环境变量 PARSER_WORKFLOW_LOG_LEVEL 控制，默认 INFO）。
- 调试时可设置: PARSER_WORKFLOW_LOG_LEVEL=DEBUG pytest tests/core/parser_workflow/ -v -s
"""
import pytest

from .test_utils import setup_parser_workflow_logging


def pytest_configure(config: pytest.Config) -> None:
    setup_parser_workflow_logging()
