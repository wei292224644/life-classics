from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import settings
from kb.clients import get_chroma_client
from kb.embeddings import embed_batch
from llm import chat as llm_chat, chat_stream
from api.search.models import ChatRequest, SearchResult, SearchResultItem
from api.shared import Paginated
from db_repositories.search import FoodSearchResult, IngredientSearchResult, SearchRepository

_chat_sessions: Dict[str, Dict[str, Any]] = {}

COLLECTION_NAME = "knowledge_base"


def _get_collection():
    return get_chroma_client().get_or_create_collection(COLLECTION_NAME)


class SearchService:

    @staticmethod
    async def search(
        query: str,
        top_k: int = 10,
        use_rerank: bool = False,
        retrieve_k: Optional[int] = None,
    ) -> List[SearchResult]:
        embeddings = await embed_batch([query])
        query_embedding = embeddings[0]
        col = _get_collection()

        n = retrieve_k or (max(top_k * 2, 20) if use_rerank else top_k)
        result = await asyncio.to_thread(
            col.query,
            query_embeddings=[query_embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        results = [
            SearchResult(
                id=ids[i],
                content=documents[i],
                metadata=metadatas[i],
                relevance_score=1.0 - distances[i],  # convert distance to score
            )
            for i in range(len(ids))
        ]

        # If rerank requested, limit to top_k (already ordered by vector similarity)
        return results[:top_k]


class ChatService:

    @staticmethod
    async def _prepare_context(request: ChatRequest) -> Tuple[List[Any], List[SearchResult]]:
        sources = await SearchService.search(
            query=request.message,
            top_k=request.top_k,
            use_rerank=request.use_rerank,
        )

        context_parts = []
        for i, src in enumerate(sources, 1):
            meta = src.metadata or {}
            standard_no = meta.get("standard_no", meta.get("doc_id", "未知文档"))
            section_path = meta.get("section_path", "")
            part = f"[文档 {i}] 来源: {standard_no}"
            if section_path:
                part += f" ({section_path})"
            part += f"\n内容: {src.content}\n"
            context_parts.append(part)

        context = "\n".join(context_parts)

        system_prompt = """你是一个专业的知识库助手。你的任务是基于提供的知识库内容回答用户的问题。

重要规则：
1. 只基于提供的知识库内容回答问题，不要编造信息
2. 如果知识库中没有相关信息，明确告诉用户
3. 回答要准确、简洁、有条理
4. 可以引用具体的文档来源

知识库内容：
{context}""".format(context=context)

        messages: List[Any] = [SystemMessage(content=system_prompt)]

        if request.conversation_history:
            for msg in request.conversation_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=request.message))
        return messages, sources

    @staticmethod
    async def chat(request: ChatRequest) -> Tuple[str, List[SearchResult]]:
        messages, sources = await ChatService._prepare_context(request)
        response = await asyncio.to_thread(
            llm_chat,
            messages=messages,
            provider_name=settings.CHAT_PROVIDER,
            model=settings.CHAT_MODEL,
            provider_config={"temperature": settings.CHAT_TEMPERATURE},
        )
        return response, sources

    @staticmethod
    def start_chat_stream(request: ChatRequest) -> str:
        session_id = str(uuid.uuid4())
        _chat_sessions[session_id] = {"request": request, "created_at": time.time()}
        return session_id

    @staticmethod
    def get_chat_session(session_id: str) -> Optional[ChatRequest]:
        session = _chat_sessions.get(session_id)
        return session["request"] if session else None

    @staticmethod
    def delete_chat_session(session_id: str) -> bool:
        if session_id in _chat_sessions:
            del _chat_sessions[session_id]
            return True
        return False

    @staticmethod
    async def chat_stream_generator(session_id: str):
        request = ChatService.get_chat_session(session_id)
        if not request:
            error_data = json.dumps({"type": "error", "data": "会话不存在或已过期"}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            return

        ChatService.delete_chat_session(session_id)

        try:
            messages, sources = await ChatService._prepare_context(request)

            sources_data = json.dumps([s.model_dump() for s in sources], ensure_ascii=False)
            yield f"data: {json.dumps({'type': 'sources', 'data': sources_data}, ensure_ascii=False)}\n\n"

            full_response = ""
            async for chunk in chat_stream(
                messages=messages,
                provider_name=settings.CHAT_PROVIDER,
                model=settings.CHAT_MODEL,
                provider_config={"temperature": settings.CHAT_TEMPERATURE},
            ):
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'data': full_response}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_data = json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"


class UnifiedSearchService:
    def __init__(self, repo: SearchRepository):
        self._repo = repo

    async def search(
        self,
        q: str,
        result_type: Literal["all", "product", "ingredient"] = "all",
        offset: int = 0,
        limit: int = 20,
    ) -> Paginated[SearchResultItem]:
        food_results: list[FoodSearchResult] = []
        ing_results: list[IngredientSearchResult] = []

        if result_type in ("all", "product"):
            food_results = await self._repo.search_foods(q)
        if result_type in ("all", "ingredient"):
            ing_results = await self._repo.search_ingredients(q)

        all_items: list[SearchResultItem] = [
            SearchResultItem(
                type="product",
                id=f.id,
                barcode=f.barcode,
                name=f.name,
                subtitle=f.product_category or "",
                riskLevel=f.risk_level,
                highRiskCount=f.high_risk_count if f.high_risk_count > 0 else None,
            )
            for f in food_results
        ] + [
            SearchResultItem(
                type="ingredient",
                id=i.id,
                name=i.name,
                subtitle="/".join(i.function_type) if i.function_type else "",
                riskLevel=i.risk_level,
            )
            for i in ing_results
        ]

        total = len(all_items)
        page = all_items[offset : offset + limit]

        return Paginated(
            items=page,
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        )
