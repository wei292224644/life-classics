"""可观测性模块：structlog 配置 + OTel SDK + Prometheus 指标。"""
from observability.configure import configure_logging, setup_otel

__all__ = ["configure_logging", "setup_otel"]
