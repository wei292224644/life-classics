"""
聊天服务
处理基于知识库的对话相关操作
"""

import json
import time
import uuid
from typing import Optional, List, Dict, Any, Tuple

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.core.config import settings
from app.core.kb.vector_store import vector_store_manager
from app.core.llm import chat as llm_chat, chat_stream
from app.api.document.models import ChatRequest, SearchResult

# 临时存储会话数据（生产环境应使用 Redis 等）
_chat_sessions: Dict[str, Dict[str, Any]] = {}


class ChatService:
    """聊天服务类"""

    @staticmethod
    async def prepare_chat_context(
        request: ChatRequest,
    ) -> Tuple[List[Any], List[SearchResult]]:
        """
        准备对话上下文（检索文档和构建消息）

        Args:
            request: 聊天请求

        Returns:
            (消息列表, 来源列表)
        """
        # 1. 从知识库检索相关文档
        if request.use_rerank:
            # 使用重排序搜索
            retrieve_k = max(request.top_k * 2, 20)
            reranked_chunks = vector_store_manager.search_with_rerank(
                query=request.message,
                top_k=request.top_k,
                retrieve_k=retrieve_k,
            )

            retrieved_docs = [chunk.document for chunk in reranked_chunks]
            sources = [
                SearchResult(
                    id=chunk.document.metadata.get("chunk_id", ""),
                    content=chunk.document.page_content,
                    metadata=chunk.document.metadata,
                    relevance_score=chunk.relevance_score,
                    relevance_reason=chunk.relevance_reason,
                )
                for chunk in reranked_chunks
            ]
        else:
            # 普通向量搜索
            retrieved_docs = vector_store_manager.search(
                query=request.message,
                top_k=request.top_k,
            )

            sources = [
                SearchResult(
                    id=doc.metadata.get("chunk_id", ""),
                    content=doc.page_content,
                    metadata=doc.metadata,
                )
                for doc in retrieved_docs
            ]

        # 2. 构建上下文
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            metadata = doc.metadata or {}
            doc_title = metadata.get("doc_title", metadata.get("doc_id", "未知文档"))
            section_path = metadata.get("section_path", [])
            section_path_str = " > ".join(section_path) if section_path else ""

            context_part = f"[文档 {i}]"
            if doc_title:
                context_part += f" 来源: {doc_title}"
            if section_path_str:
                context_part += f" ({section_path_str})"
            context_part += f"\n内容: {doc.page_content}\n"
            context_parts.append(context_part)

        context = "\n".join(context_parts)

        # 3. 构建消息列表
        messages = []

        # 系统提示
        system_prompt = """你是一个专业的知识库助手。你的任务是基于提供的知识库内容回答用户的问题。

重要规则：
1. 只基于提供的知识库内容回答问题，不要编造信息
2. 如果知识库中没有相关信息，明确告诉用户
3. 回答要准确、简洁、有条理
4. 可以引用具体的文档来源
5. 如果用户的问题与知识库内容无关，礼貌地说明你的职责范围

知识库内容：
{context}"""

        messages.append(SystemMessage(content=system_prompt.format(context=context)))

        # 对话历史
        if request.conversation_history:
            for msg in request.conversation_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # 当前用户消息
        messages.append(HumanMessage(content=request.message))

        return messages, sources

    @staticmethod
    async def chat(request: ChatRequest) -> Tuple[str, List[SearchResult]]:
        """
        基于知识库的对话（非流式）

        Args:
            request: 聊天请求

        Returns:
            (回复内容, 来源列表)
        """
        messages, sources = await ChatService.prepare_chat_context(request)

        # 调用 LLM 生成回复
        response = llm_chat(
            messages=messages,
            provider_name=settings.CHAT_PROVIDER,
            model=settings.CHAT_MODEL,
            provider_config={
                "temperature": settings.CHAT_TEMPERATURE,
                "reasoning": True,
            },
        )

        return response, sources

    @staticmethod
    def start_chat_stream(request: ChatRequest) -> str:
        """
        启动流式对话会话

        Args:
            request: 聊天请求

        Returns:
            会话 ID
        """
        session_id = str(uuid.uuid4())
        _chat_sessions[session_id] = {
            "request": request,
            "created_at": time.time(),
        }
        return session_id

    @staticmethod
    def get_chat_session(session_id: str) -> Optional[ChatRequest]:
        """
        获取聊天会话

        Args:
            session_id: 会话 ID

        Returns:
            聊天请求对象，如果不存在返回 None
        """
        if session_id not in _chat_sessions:
            return None
        session = _chat_sessions[session_id]
        return session["request"]

    @staticmethod
    def delete_chat_session(session_id: str) -> bool:
        """
        删除聊天会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        if session_id in _chat_sessions:
            del _chat_sessions[session_id]
            return True
        return False

    @staticmethod
    async def chat_stream_generator(session_id: str):
        """
        流式对话生成器

        Args:
            session_id: 会话 ID

        Yields:
            SSE 格式的数据
        """
        # 获取会话数据
        request = ChatService.get_chat_session(session_id)
        if not request:
            error_data = json.dumps(
                {"type": "error", "data": "会话不存在或已过期"}, ensure_ascii=False
            )
            yield f"data: {error_data}\n\n"
            return

        # 清理会话（使用后删除）
        ChatService.delete_chat_session(session_id)

        try:
            messages, sources = await ChatService.prepare_chat_context(request)

            # 先发送来源信息
            sources_data = json.dumps(
                [source.dict() for source in sources], ensure_ascii=False
            )
            yield f"data: {json.dumps({'type': 'sources', 'data': sources_data}, ensure_ascii=False)}\n\n"

            # 调用流式 LLM 生成回复
            full_response = ""
            async for chunk in chat_stream(
                messages=messages,
                provider_name="dashscope",
                model="qwen3-max-preview",
                provider_config={
                    "temperature": 0.4,
                    "reasoning": True,
                },
            ):
                if chunk:
                    full_response += chunk
                    # 发送文本块
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk}, ensure_ascii=False)}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'data': full_response}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback

            error_detail = traceback.format_exc()
            print(f"流式对话失败: {error_detail}")

            error_msg = str(e)
            error_data = json.dumps(
                {"type": "error", "data": error_msg}, ensure_ascii=False
            )
            yield f"data: {error_data}\n\n"
