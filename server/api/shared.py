import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def safe_http_exception(status_code: int, code: str, message: str, *, exc: Exception | None = None) -> HTTPException:
    """构造安全的 HTTP 异常，内部错误仅记录日志，不泄露给客户端."""
    if exc is not None:
        logger.error("API error %s [%d]: %s", code, status_code, str(exc))
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})
