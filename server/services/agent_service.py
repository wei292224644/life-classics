"""Agent 业务编排服务 — L2 层，调用 agent/ infra."""

from __future__ import annotations

from agent.agent import get_agent
from agent.session_store import get_session_store


class AgentService:
    """L2: Agent 业务编排 — 调用 agent/ infra."""

    def __init__(self):
        self._session_store = get_session_store()
        self._agent = get_agent()

    async def chat(self, session_id: str, message: str):
        """处理 agent 对话."""
        session = await self._session_store.get_or_create(session_id)
        actual_session_id = session["session_id"]
        response = await self._agent.arun(
            message,
            session_id=actual_session_id,
        )
        content = response.content if hasattr(response, "content") else str(response)
        return content or "", actual_session_id

    async def clear_session(self, session_id: str):
        """清除会话."""
        await self._session_store.clear(session_id)
