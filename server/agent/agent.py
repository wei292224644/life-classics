"""
统一 Agno Agent：国家标准 RAG + 食品安全助手。
"""

import logging
from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.skills import Skills
from agno.skills.loaders.local import LocalSkills
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.neo4j import Neo4jTools
from agno.tools.postgres import PostgresTools

from agent.tools.knowledge_base import knowledge_base
from agent.tools.neo4j_query import neo4j_query
from agent.tools.neo4j_vector_search import neo4j_vector_search
from config import settings

# Agno debug logging
logging.getLogger("agno").setLevel(logging.DEBUG)
logging.getLogger("agno.agent").setLevel(logging.DEBUG)
logging.getLogger("agno.tools").setLevel(logging.DEBUG)
logging.getLogger("agno.skills").setLevel(logging.DEBUG)

_agent: Optional[Agent] = None


def create_agent() -> Agent:
    """
    创建统一 Agno Agent。

    模型从环境变量读取（CHAT_MODEL / LLM_BASE_URL / LLM_API_KEY）。
    工具：knowledge_base（自定义 RAG）+ DuckDuckGo + Neo4j + PostgreSQL。
    Skills：从 agent/skills/ 目录按 Agno LocalSkills 格式加载。
    """
    model = OpenAILike(
        id=settings.DEFAULT_MODEL,
        base_url=settings.CHAT_BASE_URL or None,
        api_key=settings.CHAT_API_KEY,
        temperature=settings.CHAT_TEMPERATURE,
    )

    # 路径解析：AGENT_SKILLS_PATH 相对于 server/ 目录
    skills_path = Path(settings.AGENT_SKILLS_PATH)
    if not skills_path.is_absolute():
        skills_path = Path(__file__).parent.parent / settings.AGENT_SKILLS_PATH
    skills = Skills(loaders=[LocalSkills(path=str(skills_path))])

    tools = [knowledge_base, DuckDuckGoTools()]

    if settings.NEO4J_PASSWORD:
        tools.append(Neo4jTools(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE,
            enable_run_cypher=False,
        ))
        tools.append(neo4j_query)
        tools.append(neo4j_vector_search)

    if settings.POSTGRES_USER:
        tools.append(PostgresTools(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            db_name=settings.POSTGRES_DB,
        ))

    return Agent(
        model=model,
        tools=tools,
        skills=skills,
        debug_mode=True,
        stream_events=True,
        expected_output="""回答风格：
- 像朋友聊天一样亲切，但保持专业
- 可以用"咱们"、"咱们来看看"这样的口语化表达
- 不要写"根据查询结果"、"通过XX获取"等生硬的过渡句
- 不要展示 Cypher 代码或技术过程
- 数据用表格呈现，表格外不要加说明文字
- 结论先行，简短有力

输出结构（如果有相关内容才加，没有就不加）：
1. 直接回答问题
2. 表格（如有数据）
3. 💡 小贴士：放容易被忽略的注意事项或温馨提示""",
    )


def get_agent() -> Agent:
    """获取全局 Agent 单例（懒加载）"""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent
