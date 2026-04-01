"""
Agent 路由：/api/agent/chat
"""

from fastapi import APIRouter, HTTPException

from api.agent.models import AgentRequest, AgentResponse
from api.shared import safe_http_exception
from agent.session_store import get_session_store

router = APIRouter()

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        from agent.agent import get_agent
        _agent = get_agent()
    return _agent


@router.post("/chat", response_model=AgentResponse)
async def agent_chat(request: AgentRequest) -> AgentResponse:
    """Agent 对话（单一 Agno Agent）"""
    try:
        store = get_session_store()
        session = await store.get_or_create(request.session_id)
        session_id = session["session_id"]

        agent = _get_agent()
        response = await agent.arun(
            request.message,
            session_id=session_id,
        )

        content = response.content if hasattr(response, "content") else str(response)
        return AgentResponse(content=content or "", session_id=session_id)
    except Exception as exc:
        safe_http_exception(500, "AGENT_FAILED", "Agent execution failed", exc=exc)
