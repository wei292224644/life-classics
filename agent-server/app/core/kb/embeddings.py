from __future__ import annotations

from typing import List

from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


def _create_embedding_model() -> OpenAIEmbeddings:
    provider = settings.EMBEDDING_LLM_PROVIDER or settings.PARSER_LLM_PROVIDER
    if provider == "dashscope":
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
        )
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL or None,
    )


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """并发向量化文本列表，返回等长的向量列表。"""
    model = _create_embedding_model()
    return await model.aembed_documents(texts)
