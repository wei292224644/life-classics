"""
POST /api/logs — 接收前端错误日志，注入 trace_id 后转发至 structlog。
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Request

from api.frontend_logs.models import FrontendLogEntry

router = APIRouter()
_logger = structlog.get_logger("frontend")


@router.post("/logs", status_code=200)
async def receive_frontend_log(entry: FrontendLogEntry, request: Request):
    """
    接收前端上报的错误日志。
    - stack 字段已在 Pydantic 模型层截断（≤2000 字符）
    - 由 structlog 输出到 stdout，OTel Collector 通过 OTLP 接收
    """
    _logger.error(
        "frontend_log",
        level=entry.level.value,
        service=entry.service,
        message=entry.message,
        stack=entry.stack,
        url=entry.url,
        user_agent=entry.user_agent,
        timestamp=entry.timestamp,
        client_ip=request.client.host if request.client else None,
    )
    return {"ok": True}
