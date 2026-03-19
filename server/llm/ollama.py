"""
Ollama 提供者实现
"""

from langchain_ollama import ChatOllama, OllamaEmbeddings

from api.config import settings
from llm.utils import get_cache, get_cache_key, set_cache


base_url = settings.OLLAMA_BASE_URL


def create_chat(model: str, **kwargs) -> ChatOllama:
    cache_key = get_cache_key(f"ollama_{model}", kwargs)
    cached_instance = get_cache(cache_key)
    if cached_instance is not None:
        return cached_instance

    instance = ChatOllama(model=model, base_url=base_url, **kwargs)
    set_cache(cache_key, instance)
    return instance


def create_embedding(model: str, **kwargs) -> OllamaEmbeddings:
    cache_key = get_cache_key(f"ollama_embedding_{model}", kwargs)
    cached_instance = get_cache(cache_key)
    if cached_instance is not None:
        return cached_instance

    instance = OllamaEmbeddings(model=model, base_url=base_url, **kwargs)
    set_cache(cache_key, instance)
    return instance
