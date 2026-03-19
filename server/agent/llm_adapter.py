"""
将现有 LLM（DashScope/Ollama）适配为 LangChain BaseChatModel，供 Deep Agents 使用。
"""

from config import settings


def get_langchain_chat_model():
    """
    返回 LangChain 兼容的 Chat 模型实例。

    Returns:
        LangChain Chat model (e.g. ChatOpenAI with base_url for DashScope, or ChatOllama)
    """
    provider = (settings.CHAT_PROVIDER or "").lower()
    if provider == "dashscope":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=settings.DASHSCOPE_API_KEY,
            model=settings.CHAT_MODEL,
            temperature=getattr(settings, "CHAT_TEMPERATURE", 0.4),
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.CHAT_MODEL,
            temperature=getattr(settings, "CHAT_TEMPERATURE", 0.4),
        )
    # 默认 dashscope
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=settings.DASHSCOPE_API_KEY,
        model=settings.CHAT_MODEL,
        temperature=getattr(settings, "CHAT_TEMPERATURE", 0.4),
    )
