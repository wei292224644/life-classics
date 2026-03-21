"""FastAPI 请求日志中间件：每个请求记录方法、路径、状态码、耗时。"""
from __future__ import annotations

import time

import structlog
from fastapi import Request
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    记录每个 HTTP 请求的基本信息。
    trace_id 从当前 OTel span 中提取，与 Tempo 追踪联动。
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        # 先获取当前 span context（FastAPI instrumentation 会在此之前创建 span）
        span = trace.get_current_span()
        ctx = span.get_span_context()
        trace_id = format(ctx.trace_id, "032x") if ctx.is_valid else ""

        # 将 trace_id 注入到全局 structlog context，请求期间所有日志自动携带
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            # 请求结束后清理 trace_id，避免泄漏到后续请求
            structlog.contextvars.unbind_contextvars("trace_id")
