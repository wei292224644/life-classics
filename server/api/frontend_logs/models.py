"""前端日志上报数据模型。"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class LogLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


class FrontendLogEntry(BaseModel):
    level: LogLevel
    service: str
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str

    @field_validator("stack")
    @classmethod
    def truncate_stack(cls, v: Optional[str]) -> Optional[str]:
        """stack 截断至 2000 字符，防止超大 payload 撑爆存储。"""
        if v and len(v) > 2000:
            return v[:2000] + "...[truncated]"
        return v
