"""KB API 层 — L1 路由编排，委托 L2 KBService."""
from __future__ import annotations

from services.kb_service import KBService as L2KBService


class KBApiService:
    """L1: KB API 编排 — 委托 L2 KBService 执行实际操作."""

    def __init__(self, l2_kb_service: L2KBService):
        self._l2_kb_service = l2_kb_service

    def get_stats(self) -> dict:
        return self._l2_kb_service.get_stats()

    def clear_all(self) -> dict:
        return self._l2_kb_service.clear_all()
