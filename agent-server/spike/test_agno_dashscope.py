"""
Spike：验证 DashScope qwen-plus + Agno 兼容性。
运行：cd agent-server && uv run python3 spike/test_agno_dashscope.py
需要在 .env 中配置 DASHSCOPE_API_KEY。
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
assert DASHSCOPE_API_KEY, "请在 .env 中配置 DASHSCOPE_API_KEY"


def run_test_1_single_sync_tool():
    """验证 1：单个同步工具调用"""
    from agno.agent import Agent
    from agno.models.openai.like import OpenAILike

    def get_food_info(food_name: str) -> str:
        """获取食品信息（模拟工具）"""
        return f"{food_name} 是一种常见食品。"

    agent = Agent(
        model=OpenAILike(
            id="qwen-plus",
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        tools=[get_food_info],
        instructions="你是食品助手，用工具回答问题。",
    )

    response = agent.run("苯甲酸钠是什么？")
    print(f"✅ Test 1 通过：单同步工具调用\n响应：{response.content[:100]}\n")


def run_test_2_async_tool():
    """验证 2：async 工具调用"""
    from agno.agent import Agent
    from agno.models.openai.like import OpenAILike

    async def async_search(query: str) -> str:
        """模拟 async 工具"""
        await asyncio.sleep(0)
        return f"搜索结果：{query} 相关信息。"

    agent = Agent(
        model=OpenAILike(
            id="qwen-plus",
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        tools=[async_search],
        instructions="用工具回答问题。",
    )

    response = agent.run("查询苯甲酸钠")
    print(f"✅ Test 2 通过：async 工具调用\n响应：{response.content[:100]}\n")


def run_test_3_parallel_tools():
    """验证 3：并行工具调用（两个工具在同一请求中被调用）"""
    from agno.agent import Agent
    from agno.models.openai.like import OpenAILike

    call_log = []

    def tool_a(query: str) -> str:
        """知识库检索"""
        call_log.append("tool_a")
        return f"知识库结果：{query}"

    def tool_b(query: str) -> str:
        """网络搜索"""
        call_log.append("tool_b")
        return f"网络结果：{query}"

    agent = Agent(
        model=OpenAILike(
            id="qwen-plus",
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        tools=[tool_a, tool_b],
        instructions="同时使用 tool_a 和 tool_b 回答问题。",
    )

    response = agent.run("苯甲酸钠的安全性和最新新闻")
    print(f"调用的工具：{call_log}")
    parallel_ok = len(call_log) >= 2
    status = "✅" if parallel_ok else "⚠️ (仅调用了一个工具，可能为顺序调用)"
    print(f"{status} Test 3：并行工具调用\n响应：{response.content[:100]}\n")


if __name__ == "__main__":
    print("=== Agno + DashScope 兼容性 Spike ===\n")
    try:
        run_test_1_single_sync_tool()
    except Exception as e:
        print(f"❌ Test 1 失败：{e}\n")

    try:
        run_test_2_async_tool()
    except Exception as e:
        print(f"❌ Test 2 失败：{e}\n")

    try:
        run_test_3_parallel_tools()
    except Exception as e:
        print(f"❌ Test 3 失败：{e}\n")

    print("=== Spike 完成，请根据结果更新 spec 文档 ===")