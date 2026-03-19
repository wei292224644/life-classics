from __future__ import annotations

from typing import List

from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings

from api.config import settings


def _create_embedding_model() -> OpenAIEmbeddings:
    provider = settings.EMBEDDING_LLM_PROVIDER or settings.PARSER_LLM_PROVIDER
    if provider in {"dashscope", "openai"}:
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL or None,
        )
    if provider == "ollama":
        return OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
        )


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """并发向量化文本列表，返回等长的向量列表。"""
    model = _create_embedding_model()
    return await model.aembed_documents(texts)
