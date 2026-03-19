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


# Food Safety Agent 单例（Agno，懒加载）
_food_safety_agent = None


def _get_food_safety_agent():
    global _food_safety_agent
    if _food_safety_agent is None:
        from app.core.agent.food_safety_agent import create_food_safety_agent

        _food_safety_agent = create_food_safety_agent()
    return _food_safety_agent


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
    Agent 对话。agent_type="food_safety" 时路由到食品安全助手（Agno）。
    """
    try:
        if request.agent_type == "food_safety":
            return await _handle_food_safety_chat(request)
        else:
            return await _handle_national_standard_chat(request)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_national_standard_chat(request: AgentRequest) -> AgentResponse:
    """现有 LangGraph agent 处理逻辑（不变）"""
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
    return AgentResponse(content=content or "", sources=None, tool_calls=None)


async def _handle_food_safety_chat(request: AgentRequest) -> AgentResponse:
    """食品安全助手（Agno）处理逻辑"""
    from app.core.agent.session_store import get_session_store

    store = get_session_store()
    session = await store.get_or_create(request.session_id)

    agent = _get_food_safety_agent()

    # ⚠️ 必须用 agent.arun()（async），不能用 agent.run()（sync）
    # knowledge_base 是 async def，agent.arun() 自动处理
    response = await agent.arun(request.message, session_id=session["session_id"])

    content = response.content if hasattr(response, "content") else str(response)
    return AgentResponse(content=content or "", sources=None, tool_calls=None)
