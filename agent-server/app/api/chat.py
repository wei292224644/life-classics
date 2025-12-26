"""
对话API - 基于知识库的多轮对话 (LangChain版本)
"""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.vector_store import vector_store_manager
from app.core.llm import get_llm
from app.core.tools import get_web_search_tool
from langchain.agents.factory import create_agent
from langchain_core.tools import Tool
from app.core.config import settings

router = APIRouter()

# 缓存chat engine实例，避免每次请求都重新创建
chat_engine_cache: Dict[str, any] = {}


class ChatMessageRequest(BaseModel):
    """对话消息请求模型"""

    message: str
    top_k: Optional[int] = 5  # 检索相关文档数量
    stream: Optional[bool] = False  # 是否流式返回（暂不支持）


class ChatMessageResponse(BaseModel):
    """对话消息响应模型"""

    answer: str
    sources: List[Dict]  # 相关文档来源
    metadata: Dict
    token_usage: Optional[Dict] = None  # Token 使用情况


class ChatHistoryResponse(BaseModel):
    """对话历史响应模型"""

    messages: List[Dict]
    total_messages: int


def _get_or_create_chat_engine(top_k: int = 5):
    """
    获取或创建对话引擎

    使用 LangChain Agent 来管理对话历史和上下文
    """
    if (
        not hasattr(vector_store_manager, "vector_store")
        or not vector_store_manager.vector_store
    ):
        raise HTTPException(status_code=500, detail="向量索引未初始化，请先上传文档")

    # 获取LLM
    llm = get_llm("dashscope")

    # 创建知识库查询工具
    def query_knowledge_base(query: str) -> str:
        """查询本地知识库获取相关信息"""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] query_knowledge_base 被调用，query={query!r}")
        print(f"[DEBUG] query_knowledge_base 被调用，query={query!r}")

        try:
            # 使用向量存储的检索器
            retriever = vector_store_manager.get_retriever(top_k=top_k)
            # LangChain 1.x 中 retriever 使用 invoke 方法
            docs = retriever.invoke(query)

            if not docs:
                return "知识库中没有找到相关信息。"

            # 格式化检索到的文档
            result_texts = []
            for i, doc in enumerate(docs[:top_k], 1):
                text = (
                    doc.page_content[:500] + "..."
                    if len(doc.page_content) > 500
                    else doc.page_content
                )
                result_texts.append(f"[文档{i}]\n{text}")

            result = "\n\n".join(result_texts)
            logger.info(f"[DEBUG] query_knowledge_base 返回结果长度: {len(result)}")
            return result
        except Exception as e:
            logger.error(f"[DEBUG] query_knowledge_base 出错: {e}")
            return f"查询知识库时出错: {str(e)}"

    # 创建工具列表
    kb_tool = Tool(
        name="query_knowledge_base",
        func=query_knowledge_base,
        description=("查询本地知识库获取相关信息。"),
    )

    web_search_tool = get_web_search_tool()

    tools = [kb_tool, web_search_tool]

    # 创建系统提示（字符串格式）
    # create_agent 的 system_prompt 参数需要字符串，不是 ChatPromptTemplate
    system_prompt = """你是一名食品安全领域的专业问答助手。

你的回答必须以提供的食品安全知识库内容为第一信息来源。
禁止编造事实、数据、标准、法规或结论。

无论任何情况，你都必须输出一条完整的自然语言回答。

如果知识库中没有与用户问题直接相关的信息，
你必须明确说明不知道，禁止任何推测性回答。

你具备联网查阅能力，但该能力受到严格限制，
仅在明确需要"近期 / 最新 / 时效性信息"时才允许使用。当用户明确要求"最新 / 近期 / 最近"的信息，或问题本身明显具有时间敏感性，且知识库中未包含相关信息时，才允许使用。

回答流程必须严格遵循以下顺序：
1. 先判断知识库内容是否能够直接回答用户问题，如果可以，仅基于知识库内容作答。
2. 仅当同时满足以下条件时，才允许联网查询：用户明确要求"最新 / 近期 / 最近"的信息，或问题本身明显具有时间敏感性，且知识库中未包含相关信息
3. 若知识库无法回答，且不满足联网条件，必须明确说明不知道，禁止任何推测性回答。

重要：当调用 web_search 工具时，query 参数必须是用户原始问题的核心关键词，不要使用知识库检索到的无关内容。
例如：用户问"北京今天天气怎么样"，web_search 的 query 应该是用户的问题，而不是知识库中检索到的其他内容。
"""

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    return agent


@router.post("/", response_model=ChatMessageResponse)
async def chat(request: ChatMessageRequest):
    """
    发送消息并获取AI回答

    支持多轮对话，会自动维护对话历史
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    # 获取或创建对话引擎
    chat_engine = _get_or_create_chat_engine(top_k=request.top_k)

    # 发送消息并获取回答
    # create_agent 返回的 agent 使用 messages 格式
    from langchain_core.messages import HumanMessage

    # 添加调试日志
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG] 用户输入: {request.message!r}")

    # 尝试使用 messages 格式
    try:
        response = chat_engine.invoke(
            {"messages": [HumanMessage(content=request.message)]},
        )
        # 提取答案 - response 可能是消息列表或字典
        if hasattr(response, "messages") and response.messages:
            answer = response.messages[-1].content
        elif isinstance(response, dict):
            if "messages" in response and response["messages"]:
                answer = response["messages"][-1].content
            elif "output" in response:
                answer = response["output"]
            else:
                answer = str(response)
        else:
            answer = str(response)
    except Exception as e:
        # 如果 messages 格式失败，尝试 input 格式
        logger.warning(f"[DEBUG] messages 格式失败，尝试 input 格式: {e}")
        try:
            response = chat_engine.invoke(
                {"input": request.message},
                config={"callbacks": [token_callback]},
            )
            answer = response.get("output", str(response))
        except Exception as e2:
            logger.error(f"[DEBUG] invoke 失败: {e2}")
            raise HTTPException(status_code=500, detail=f"Agent 执行失败: {str(e2)}")

    # 提取来源信息
    # initialize_agent 的 AgentExecutor 不直接提供 source_nodes
    # 可以通过 agent_executor.agent.llm_chain.memory 或其他方式获取
    sources = []

    # 获取 token 使用情况
    token_usage = token_callback.get_usage()

    return ChatMessageResponse(
        answer=answer,
        sources=sources,
        metadata={"query": request.message, "top_k": request.top_k},
        token_usage=token_usage,
    )
