"""
Agent 路由：/api/agent/chat 等。
"""

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.api.agent.models import AgentRequest, AgentResponse, SearchResult

router = APIRouter()

# 单例 Agent（懒加载，避免启动时拉取 Chroma/Reranker）
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        from app.core.agent.factory import create_national_standard_agent

        _agent = create_national_standard_agent()
    return _agent


def _build_messages(request: AgentRequest) -> List[Dict[str, str]]:
    messages = []
    for item in request.conversation_history or []:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role == "user":
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "assistant", "content": content})
    messages.append({"role": "user", "content": request.message})
    return messages


def _invoke_agent_sync(messages: List[Dict], thread_id: str) -> Dict[str, Any]:
    agent = _get_agent()
    config = {"configurable": {"thread_id": thread_id or "default"}}
    # LangGraph 状态通常为 {"messages": [...]}
    result = agent.invoke(
        {"messages": messages},
        config=config,
    )
    return result


def _extract_response_content(state: Dict[str, Any]) -> str:
    messages = state.get("messages") or []
    for m in reversed(messages):
        content = None
        if hasattr(m, "content"):
            content = m.content
        elif isinstance(m, dict):
            if m.get("role") in ("assistant", "ai"):
                content = m.get("content", "")
        if content is not None and content != "":
            return content if isinstance(content, str) else str(content)
    return ""


@router.post("/chat", response_model=AgentResponse)
async def agent_chat(request: AgentRequest) -> AgentResponse:
    """
    Agent 对话（多工具编排：知识库 / 网络 / Neo4j / PostgreSQL）。
    """
    try:
        messages = _build_messages(request)
        thread_id = request.thread_id or "default"
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            None,
            _invoke_agent_sync,
            messages,
            thread_id,
        )
        content = _extract_response_content(state)
        # 若需返回 sources / tool_calls，可从 state 中解析 tool_calls 等
        return AgentResponse(content=content or "", sources=None, tool_calls=None)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
