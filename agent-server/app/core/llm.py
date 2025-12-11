"""
LLM配置 - 使用Qwen模型
"""

from app.core.config import settings

# 动态导入DashScope，如果不可用则提示错误
try:
    from llama_index.llms.dashscope import DashScope
except ImportError:
    DashScope = None
    import warnings

    warnings.warn("无法导入DashScope，请安装: pip install llama-index-llms-dashscope")


def get_llm():
    """获取Qwen LLM实例"""
    if not settings.DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY未设置，请在.env文件中配置")

    if DashScope is None:
        raise ImportError(
            "DashScope LLM不可用，请安装: pip install llama-index-llms-dashscope"
        )

    return DashScope(
        model=settings.QWEN_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        temperature=0.7,
        max_tokens=2048,
    )
