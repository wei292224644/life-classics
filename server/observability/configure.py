"""structlog 全局初始化 + OpenTelemetry SDK 配置（traces + logs）。"""
from __future__ import annotations

import logging
import sys

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_logging(log_level: str = "INFO", service_name: str = "life-classics-server") -> None:
    """
    配置 structlog 输出 JSON 格式日志到 stdout。
    同时将 service_name 注入为全局上下文变量，每条日志自动携带。
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 将 service 注入为全局上下文，所有日志自动携带
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)

    # 标准库 logging 基础配置（给第三方库用）
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=False,
    )


def setup_otel(
    otlp_endpoint: str,
    service_name: str,
) -> TracerProvider:
    """
    初始化 OpenTelemetry TracerProvider + LoggerProvider。
    将 traces 和 logs 通过 OTLP/HTTP 导出到 OTel Collector。
    """
    # 幂等保护：避免重复初始化（热重载、测试多次调用等场景）
    existing = trace.get_tracer_provider()
    if isinstance(existing, TracerProvider):
        return existing

    resource = Resource.create({"service.name": service_name})

    # ── Traces ────────────────────────────────────────────────────────────────
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # 将 trace_id 注入标准库 logging（structlog 桥接后自动携带）
    LoggingInstrumentor().instrument(set_logging_format=False)

    return tracer_provider
