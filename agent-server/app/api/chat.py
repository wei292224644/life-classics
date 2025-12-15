"""
对话API - 基于知识库的多轮对话
"""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.vector_store import vector_store_manager
from app.core.llm import get_llm

# 尝试多种导入路径以兼容不同版本的 LlamaIndex
try:
    from llama_index.core.base.llms.types import ChatMessage, MessageRole
except ImportError:
    try:
        from llama_index.core.chat_engine.types import ChatMessage
        from llama_index.core.base.llms.types import MessageRole
    except ImportError:
        try:
            from llama_index.core.llms.types import MessageRole
            from llama_index.core.chat_engine.types import ChatMessage
        except ImportError:
            # 如果都失败，定义简单的替代类
            from enum import Enum

            class MessageRole(str, Enum):
                USER = "user"
                ASSISTANT = "assistant"
                SYSTEM = "system"

            class ChatMessage:
                def __init__(self, role, content: str):
                    # 支持字符串或 MessageRole 枚举
                    if isinstance(role, str):
                        # 将字符串转换为对应的 MessageRole
                        role_map = {
                            "user": MessageRole.USER,
                            "assistant": MessageRole.ASSISTANT,
                            "system": MessageRole.SYSTEM,
                        }
                        self.role = role_map.get(role.lower(), MessageRole.USER)
                    elif isinstance(role, MessageRole):
                        self.role = role
                    else:
                        # 如果已经是 MessageRole 实例，直接使用
                        self.role = role
                    self.content = content


router = APIRouter()

# 缓存chat engine实例，避免每次请求都重新创建
chat_engine_cache: Dict[str, any] = {}


class ChatMessageRequest(BaseModel):
    """对话消息请求模型"""

    message: str
    conversation_id: Optional[str] = "default"  # 对话ID，用于区分不同对话
    top_k: Optional[int] = 5  # 检索相关文档数量
    stream: Optional[bool] = False  # 是否流式返回（暂不支持）


class ChatMessageResponse(BaseModel):
    """对话消息响应模型"""

    answer: str
    conversation_id: str
    sources: List[Dict]  # 相关文档来源
    metadata: Dict


class ChatHistoryResponse(BaseModel):
    """对话历史响应模型"""

    conversation_id: str
    messages: List[Dict]
    total_messages: int


def _get_or_create_chat_engine(conversation_id: str, top_k: int = 5):
    """
    获取或创建对话引擎

    使用 ChatEngine 来管理对话历史和上下文
    支持父子chunk模式（如果启用）
    """
    if not vector_store_manager.index:
        raise HTTPException(status_code=500, detail="向量索引未初始化，请先上传文档")

    # 暂时禁用缓存，每次都重新创建engine以确保状态正确
    # 这样可以避免缓存导致的状态问题
    # cache_key = f"{conversation_id}_{top_k}"
    # if cache_key in chat_engine_cache:
    #     return chat_engine_cache[cache_key]

    try:
        from llama_index.core.chat_engine import ContextChatEngine
        from llama_index.core.memory import ChatMemoryBuffer
        from app.core.config import settings

        # 获取对话历史

        # 创建检索器（支持父子chunk模式）
        if settings.ENABLE_PARENT_CHILD:
            # 使用AutoMergingRetriever（与vector_store中的逻辑一致）
            try:
                from llama_index.core.retrievers import AutoMergingRetriever
                from llama_index.core.retrievers import VectorIndexRetriever

                vector_retriever = VectorIndexRetriever(
                    index=vector_store_manager.index,
                    similarity_top_k=top_k * 3,  # 检索更多子节点
                )

                # AutoMergingRetriever 的正确参数是 vector_retriever 而不是 base_retriever
                retriever = AutoMergingRetriever(
                    vector_retriever=vector_retriever,
                    storage_context=vector_store_manager.storage_context,
                    verbose=False,
                )
            except (ImportError, TypeError) as e:
                # 如果参数错误或导入失败，回退到普通检索器
                print(
                    f"警告: AutoMergingRetriever 不可用或参数错误: {e}，回退到普通检索器"
                )
                retriever = vector_store_manager.index.as_retriever(
                    similarity_top_k=top_k
                )
        else:
            # 普通检索器
            try:
                retriever = vector_store_manager.index.as_retriever(
                    similarity_top_k=top_k
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"创建检索器失败: {str(e)}")

        # 创建上下文对话引擎
        # ContextChatEngine 会自动：
        # 1. 从知识库检索相关文档
        # 2. 将检索到的文档作为上下文
        # 3. 结合对话历史生成回答
        chat_engine = ContextChatEngine.from_defaults(
            retriever=retriever,
            llm=get_llm("ollama", {"model": settings.OLLAMA_MODEL}),
            system_prompt=(
                "你是一个基于知识库的专业问答助手。"
                # "你的所有回答必须严格来源于提供给你的知识库内容。"
                # "你不具备超出知识库的常识补全能力，也不允许凭经验或推测作答。"
                # "如果没有信息，应该说不知道"
                # "核心原则："
                # "1. 只基于知识库回答。"
                # "只能使用检索到的知识库内容进行回答，不得引入外部知识、常识或推断。"
                # "2. 没有信息就明确说不知道。"
                # "如果知识库中没有与用户问题直接相关的信息，必须明确回答："
                # "“知识库中没有相关信息，无法回答该问题。”"
                # "或："
                # "“当前知识库未包含该问题所需的信息。”"
                # "不得尝试合理猜测或推测性补全。"
                # "3. 禁止编造。"
                # "不得编造事实、数据、结论、标准、定义。"
                # "不得使用“通常来说 / 一般情况下 / 可能是”等模糊表达。"
            ),
        )

        # 暂时禁用缓存
        # chat_engine_cache[cache_key] = chat_engine

        return chat_engine
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"无法导入必要的模块: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建对话引擎失败: {str(e)}")


@router.post("/", response_model=ChatMessageResponse)
async def chat(request: ChatMessageRequest):
    """
    发送消息并获取AI回答

    支持多轮对话，会自动维护对话历史
    """
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="消息内容不能为空")

        # 获取或创建对话引擎
        chat_engine = _get_or_create_chat_engine(
            conversation_id=request.conversation_id, top_k=request.top_k
        )

        # 发送消息并获取回答
        response = chat_engine.chat(request.message)

        # 提取答案
        if hasattr(response, "response"):
            answer = str(response.response)
        else:
            # 回退到str()方法
            answer = str(response)

        # 提取来源信息
        sources = []
        if hasattr(response, "source_nodes") and response.source_nodes:
            for node in response.source_nodes:
                source_info = {
                    "text": (
                        node.text[:300] + "..." if len(node.text) > 300 else node.text
                    ),
                    "score": getattr(node, "score", None),
                    "metadata": node.metadata if hasattr(node, "metadata") else {},
                }
                sources.append(source_info)

        # 从 chat_engine 的 memory 中获取更新后的历史记录
        # ChatMemoryBuffer 会自动管理历史，我们需要同步到我们的存储中
        if hasattr(chat_engine, "memory") and hasattr(chat_engine.memory, "get_all"):
            chat_engine.memory.get_all()

        return ChatMessageResponse(
            answer=answer,
            conversation_id=request.conversation_id,
            sources=sources,
            metadata={"query": request.message, "top_k": request.top_k},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")
