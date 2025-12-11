"""
嵌入模型配置 - Qwen
"""
from app.core.config import settings

try:
    from llama_index.embeddings.dashscope import DashScopeEmbedding
except ImportError:
    DashScopeEmbedding = None
    import warnings

    warnings.warn("无法导入DashScopeEmbedding，请安装: pip install llama-index-embeddings-dashscope")


def get_embedding_model():
    """获取Qwen嵌入模型"""
    if not settings.DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY未设置，请在.env文件中配置")

    if DashScopeEmbedding is None:
        raise ImportError("DashScopeEmbedding 不可用，请安装: pip install llama-index-embeddings-dashscope")

    return DashScopeEmbedding(
        model_name=settings.QWEN_EMBEDDING_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
    )

