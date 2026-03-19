"""
食品安全 AI 助手 Agent（Agno + DashScope qwen-plus）。
"""
import logging
from typing import Optional

from agno.agent import Agent
from agno.models.openai.like import OpenAILike

from agent.skill_loader import load_skills
from config import settings

logger = logging.getLogger(__name__)

_agent: Optional[Agent] = None


def _make_web_search_tool():
    """获取 web_search 工具函数（同步）。"""
    from agent.tools.web_search import web_search_tool_function

    def web_search(query: str, num_results: int = 5) -> str:
        """
        搜索互联网，仅用于查询品牌、企业召回、食品安全事件等时效性信息。
        不用于查询标准知识。
        """
        try:
            return web_search_tool_function(query, num_results)
        except Exception as e:
            logger.warning(f"web_search 工具调用失败: {e}")
            return "网络搜索失败。"

    return web_search


def create_food_safety_agent() -> Agent:
    """
    创建食品安全 AI 助手 Agent。

    注意：knowledge_base 是 async def 工具，Agno 会通过 agent.arun() 自动处理。
    不要包装为同步函数，直接传入即可。

    Returns:
        配置好的 Agno Agent 实例
    """
    from agent.tools.knowledge_base import knowledge_base

    instructions = load_skills()

    agent = Agent(
        model=OpenAILike(
            id="qwen-plus",
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        instructions=instructions,
        tools=[knowledge_base, _make_web_search_tool()],
    )

    return agent


def get_food_safety_agent() -> Agent:
    """获取全局 FoodSafetyAgent 单例（懒加载）"""
    global _agent
    if _agent is None:
        _agent = create_food_safety_agent()
    return _agent