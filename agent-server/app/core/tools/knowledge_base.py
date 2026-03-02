"""
知识库检索工具：供 Agent 基于向量库检索国家标准等内容。
"""

from langchain_core.tools import tool

from app.core.kb.vector_store import vector_store_manager


@tool
def knowledge_base(query: str, top_k: int = 5) -> str:
    """
    从知识库中检索与查询最相关的文档片段（国家标准等）。适合回答与已入库文档相关的问题。

    Args:
        query: 检索查询文本
        top_k: 返回条数，默认 5

    Returns:
        格式化后的检索结果文本，包含内容与来源信息
    """
    retrieve_k = max(top_k * 2, 10)
    try:
        chunks = vector_store_manager.search_with_rerank(
            query, top_k=top_k, retrieve_k=retrieve_k
        )
    except Exception as e:
        return f"知识库检索失败: {e!s}"
    if not chunks:
        return "未检索到相关文档。"
    lines = []
    for i, c in enumerate(chunks, 1):
        content = c.document.page_content if hasattr(c, "document") else str(c)
        meta = c.document.metadata if hasattr(c, "document") and c.document.metadata else {}
        score = getattr(c, "relevance_score", None)
        part = f"[{i}] {content}"
        if meta:
            part += f"\n  来源: {meta}"
        if score is not None:
            part += f"\n  相关度: {score:.2f}"
        lines.append(part)
    return "\n\n".join(lines)
