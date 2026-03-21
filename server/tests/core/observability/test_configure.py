"""测试 structlog 配置和 OTel 初始化。"""
import json
import structlog
import pytest
from observability.configure import configure_logging


@pytest.fixture(autouse=True)
def reset_structlog():
    """每个测试前后重置 structlog 全局状态，避免 cache_logger_on_first_use 跨测试污染。"""
    yield
    structlog.reset_defaults()


def test_structlog_outputs_json(capsys):
    """配置后 structlog 应输出 JSON 格式，且包含指定字段。"""
    configure_logging(log_level="DEBUG", service_name="test-service")
    logger = structlog.get_logger()
    logger.info("hello world", user="alice")

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l]
    assert lines, "没有任何输出"
    record = json.loads(lines[-1])
    assert record["event"] == "hello world"
    assert record["user"] == "alice"
    assert "timestamp" in record
    assert record.get("service") == "test-service"


def test_structlog_includes_level(capsys):
    """WARNING 日志应包含 level 字段且值为 warning。"""
    configure_logging(log_level="WARNING", service_name="test-service")
    logger = structlog.get_logger()
    logger.warning("test warning")

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l]
    assert lines, "没有任何输出"
    record = json.loads(lines[-1])
    assert record.get("level") == "warning"
