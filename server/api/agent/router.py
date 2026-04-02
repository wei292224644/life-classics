"""
Agent 路由：/api/agent/chat
"""

from fastapi import APIRouter, Depends

from api.agent.models import AgentRequest, AgentResponse
from api.shared import safe_http_exception
from services.agent_service import AgentService

router = APIRouter()


def get_agent_service() -> AgentService:
    """L2 依赖注入: Agent 业务服务."""
    return AgentService()


@router.post("/chat", response_model=AgentResponse)
async def agent_chat(
    request: AgentRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Agent 对话（单一 Agno Agent）"""
    try:
        content, session_id = await agent_service.chat(request.session_id, request.message)
        return AgentResponse(content=content, session_id=session_id)
    except Exception as exc:
        safe_http_exception(500, "AGENT_FAILED", "Agent execution failed", exc=exc)
