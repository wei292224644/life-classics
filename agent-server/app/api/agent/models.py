"""
Agent 请求/响应模型。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AgentRequest(BaseModel):
    """Agent 对话请求"""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    thread_id: Optional[str] = None          # 现有字段，保留（LangGraph agent 使用）
    agent_type: Optional[str] = None         # 新增：路由到哪个 agent（"food_safety" 或 None）
    session_id: Optional[str] = None         # 新增：Agno session ID（多轮对话）
    config: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """检索来源项（与 document 模块对齐）"""
    id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None


class AgentResponse(BaseModel):
    """Agent 对话响应"""
    content: str
    sources: Optional[List[SearchResult]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
