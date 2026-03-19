"""
创建国家标准 RAG Agent（Deep Agents + Tools）。
"""

from app.core.config import settings
from app.core.agent.llm_adapter import get_langchain_chat_model
from app.core.tools import (
    get_web_search_tool,
    knowledge_base,
    neo4j_query,
    postgres_query,
)


def create_national_standard_agent(
    skills_path: str = None,
    tools=None,
    **kwargs
):
    """
    创建国家标准 RAG Agent。

    Args:
        skills_path: Skills 目录路径（预留，Deep Agents 需通过 backend 提供 skills 文件）
        tools: 工具列表，默认使用 knowledge_base / web_search / neo4j_query / postgres_query
        **kwargs: 透传给 create_deep_agent（如 system_prompt, max_iterations）

    Returns:
        编译后的 LangGraph Agent（CompiledStateGraph）
    """
    from deepagents import create_deep_agent

    model = get_langchain_chat_model()
    if tools is None:
        tools = [
            knowledge_base,
            get_web_search_tool(),
            neo4j_query,
            postgres_query,
        ]
    system_prompt = kwargs.pop(
        "system_prompt",
        "你是基于国家标准的智能助手。优先使用 knowledge_base 工具检索已入库文档；需要最新或外部信息时使用 web_search；需要图关系时使用 neo4j_query；需要结构化数据时使用 postgres_query。回答请基于检索结果，并注明来源。",
    )
    skills_path = skills_path or getattr(settings, "AGENT_SKILLS_PATH", "app/skills")
    # skills 需通过 Deep Agents 的 backend 提供文件，此处仅传默认路径供后续扩展
    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        **kwargs,
    )
